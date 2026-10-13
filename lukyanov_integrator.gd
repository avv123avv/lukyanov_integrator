class_name LukyanovIntegrator
extends Node2D
## Симуляция одномерного гидравлического интегратора Лукьянова.
## Повесьте скрипт на Node2D в новой сцене и запустите.
##
## Управление:
##   ↑ / ↓   — поднять / опустить бак на 1 см
##   Пробел  — пауза
##   + / −   — ускорить / замедлить время (x2)
##   R       — сброс
##   S       — сохранить замеры в CSV
##   L       — язык интерфейса (ru / en)

@export var vessel_count: int = 5
@export var vessel_height_cm: float = 25.0
## За сколько секунд разница уровней в паре соседних сосудов падает вдвое.
## Берётся из калибровки реальной установки.
@export var pair_half_time_s: float = 20.0
@export var tank_level_cm: float = 0.0
@export var outlet_level_cm: float = 0.0
@export var start_level_cm: float = 0.0
@export var sim_speed: float = 1.0
@export var record_interval_s: float = 5.0

const PX_PER_CM := 14.0
const VESSEL_W := 44.0
const GAP := 36.0
const BASE_Y := 540.0
const LEFT_X := 60.0
const TUBE_Y_OFFSET := 6.0

const COLOR_WATER := Color(0.27, 0.55, 0.87)
const COLOR_GLASS := Color(0.85, 0.85, 0.85)
const COLOR_CLAMP := Color(0.92, 0.62, 0.15)
const COLOR_PROFILE := Color(0.85, 0.35, 0.19)
const COLOR_TEXT := Color(0.92, 0.92, 0.92)

var levels: PackedFloat64Array
var sim_time := 0.0
var paused := false
var _record_timer := 0.0
var _log: PackedStringArray = []


func _ready() -> void:
	_reset()


func _reset() -> void:
	levels = PackedFloat64Array()
	levels.resize(vessel_count)
	levels.fill(start_level_cm)
	sim_time = 0.0
	_record_timer = 0.0
	_log.clear()
	_log.append(_csv_header())
	_log.append(_csv_row())
	queue_redraw()


## Постоянная времени одной ячейки: τ = A / G.
## Для пары сосудов Δh(t) = Δh0 · exp(−2t/τ), отсюда τ = 2 · t½ / ln2.
func _tau() -> float:
	return 2.0 * pair_half_time_s / log(2.0)


func _process(delta: float) -> void:
	if paused:
		return
	var t := delta * sim_speed
	var tau := _tau()
	# Явная схема устойчива при dt/τ ≤ 0.5, берём с запасом.
	var steps := maxi(1, int(ceil(t / (tau * 0.2))))
	var dt := t / steps
	for s in steps:
		_step(dt, tau)
	sim_time += t
	_record_timer += t
	while _record_timer >= record_interval_s:
		_record_timer -= record_interval_s
		_log.append(_csv_row())
	queue_redraw()


## dh_i/dt = (h_{i-1} − 2·h_i + h_{i+1}) / τ — то же уравнение, что и для тепла.
func _step(dt: float, tau: float) -> void:
	var n := levels.size()
	var next := levels.duplicate()
	for i in n:
		var left: float = tank_level_cm if i == 0 else levels[i - 1]
		var right: float = outlet_level_cm if i == n - 1 else levels[i + 1]
		var h: float = levels[i] + dt / tau * (left - 2.0 * levels[i] + right)
		next[i] = clampf(h, 0.0, vessel_height_cm)
	levels = next


func _unhandled_input(event: InputEvent) -> void:
	var key := event as InputEventKey
	if key == null or not key.pressed:
		return
	match key.keycode:
		KEY_UP:
			tank_level_cm = minf(tank_level_cm + 1.0, vessel_height_cm)
		KEY_DOWN:
			tank_level_cm = maxf(tank_level_cm - 1.0, 0.0)
		KEY_SPACE:
			paused = not paused
		KEY_EQUAL, KEY_KP_ADD:
			sim_speed = minf(sim_speed * 2.0, 256.0)
		KEY_MINUS, KEY_KP_SUBTRACT:
			sim_speed = maxf(sim_speed / 2.0, 0.125)
		KEY_R:
			_reset()
		KEY_S:
			_save_csv()
		KEY_L:
			I18n.toggle()
	queue_redraw()


# --- CSV ---------------------------------------------------------------

func _csv_header() -> String:
	var cols := PackedStringArray(["t_s", "tank_cm"])
	for i in vessel_count:
		cols.append("h%d_cm" % (i + 1))
	return ",".join(cols)


func _csv_row() -> String:
	var cols := PackedStringArray(["%.1f" % sim_time, "%.1f" % tank_level_cm])
	for h in levels:
		cols.append("%.2f" % h)
	return ",".join(cols)


func _save_csv() -> bool:
	var path := "user://lukyanov_levels.csv"
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		push_error("Не удалось сохранить CSV: %s" % error_string(FileAccess.get_open_error()))
		return false
	f.store_string("\n".join(_log) + "\n")
	f.close()
	print("Сохранено: ", ProjectSettings.globalize_path(path))
	return true


# --- Отрисовка ----------------------------------------------------------

func _y(level_cm: float) -> float:
	return BASE_Y - level_cm * PX_PER_CM


func _vessel_x(i: int) -> float:
	return LEFT_X + (i + 1) * (VESSEL_W + GAP)


func _draw() -> void:
	var font := ThemeDB.fallback_font
	var fs := 14
	var tube_y := BASE_Y - TUBE_Y_OFFSET
	var top_y := _y(vessel_height_cm)

	# Бак: поверхность воды на уровне tank_level_cm
	var tank_x := LEFT_X
	var tank_surface := _y(tank_level_cm)
	var tank_bottom := tank_surface + 40.0
	draw_rect(Rect2(tank_x, tank_surface, VESSEL_W, tank_bottom - tank_surface), COLOR_WATER)
	_draw_open_box(tank_x, tank_surface - 20.0, tank_bottom)
	var tank_cx := tank_x + VESSEL_W * 0.5
	if tank_bottom < tube_y:
		draw_line(Vector2(tank_cx, tank_bottom), Vector2(tank_cx, tube_y), COLOR_WATER, 5.0)
	draw_string(font, Vector2(tank_x - 6, tank_surface - 28), I18n.t("Бак"), HORIZONTAL_ALIGNMENT_LEFT, -1, fs, COLOR_TEXT)

	# Трубки с кранами
	var x_prev := tank_cx
	for i in vessel_count:
		var x := _vessel_x(i)
		draw_line(Vector2(x_prev, tube_y), Vector2(x, tube_y), COLOR_WATER, 5.0)
		_draw_clamp((x_prev + x) * 0.5, tube_y)
		x_prev = x + VESSEL_W
	var outlet_x := x_prev + GAP + 10.0
	draw_line(Vector2(x_prev, tube_y), Vector2(outlet_x, tube_y), COLOR_WATER, 5.0)
	_draw_clamp((x_prev + outlet_x) * 0.5, tube_y)

	# Сосуды
	for i in vessel_count:
		var x := _vessel_x(i)
		var wy := _y(levels[i])
		draw_rect(Rect2(x, wy, VESSEL_W, BASE_Y - wy), COLOR_WATER)
		_draw_open_box(x, top_y, BASE_Y)
		draw_string(font, Vector2(x, BASE_Y + 22), "%.1f" % levels[i], HORIZONTAL_ALIGNMENT_CENTER, VESSEL_W, fs, COLOR_TEXT)

	# Слив с постоянным уровнем
	var oy := _y(outlet_level_cm)
	draw_line(Vector2(outlet_x - 4, oy), Vector2(outlet_x + 30, oy), COLOR_GLASS, 2.0)
	draw_string(font, Vector2(outlet_x - 4, oy - 8), I18n.t("Слив"), HORIZONTAL_ALIGNMENT_LEFT, -1, fs, COLOR_TEXT)

	# Профиль «температуры»
	var pts: Array[Vector2] = [Vector2(tank_cx, tank_surface)]
	for i in vessel_count:
		pts.append(Vector2(_vessel_x(i) + VESSEL_W * 0.5, _y(levels[i])))
	pts.append(Vector2(outlet_x + 13, oy))
	for i in pts.size() - 1:
		draw_dashed_line(pts[i], pts[i + 1], COLOR_PROFILE, 2.0, 6.0)

	# Информация
	var info := PackedStringArray([
		I18n.t("t = %.0f с   скорость x%s%s") % [sim_time, str(sim_speed), I18n.t("   [пауза]") if paused else ""],
		I18n.t("Бак: %.0f см   слив: %.0f см   τ = %.1f с") % [tank_level_cm, outlet_level_cm, _tau()],
		I18n.t("↑↓ бак   Пробел пауза   +/− скорость   R сброс   S сохранить CSV   L язык"),
	])
	for i in info.size():
		draw_string(font, Vector2(16, 28 + i * 22), info[i], HORIZONTAL_ALIGNMENT_LEFT, -1, fs, COLOR_TEXT)


func _draw_open_box(x: float, y_top: float, y_bottom: float) -> void:
	var pts := PackedVector2Array([
		Vector2(x, y_top), Vector2(x, y_bottom),
		Vector2(x + VESSEL_W, y_bottom), Vector2(x + VESSEL_W, y_top),
	])
	draw_polyline(pts, COLOR_GLASS, 2.0)


func _draw_clamp(cx: float, cy: float) -> void:
	draw_rect(Rect2(cx - 4, cy - 9, 8, 18), COLOR_CLAMP)

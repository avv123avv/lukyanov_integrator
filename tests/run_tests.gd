extends SceneTree
## Автотесты: godot --headless --path . -s tests/run_tests.gd
## Код выхода 0 — всё прошло, 1 — есть провалы (так их видит CI).

const SETTINGS := "user://settings.cfg"

var _failed := 0
var _passed := 0


func _check(ok: bool, what: String) -> void:
	if ok:
		_passed += 1
		print("  ok   ", what)
	else:
		_failed += 1
		printerr("  FAIL ", what)


func _new_rig() -> Node2D:
	var rig: Node2D = load("res://syringe_rig.tscn").instantiate()
	root.add_child(rig)
	return rig


## Явный Эйлер напрямую, без _process: время не зависит от кадров.
func _run(rig: Node2D, seconds: float) -> void:
	var tau: float = rig._tau()
	var dt := tau * 0.05
	var t := 0.0
	while t < seconds:
		rig._step(dt, tau)
		t += dt


func _click(rig: Node2D, pos: Vector2, index := MOUSE_BUTTON_LEFT, pressed := true) -> void:
	var e := InputEventMouseButton.new()
	e.button_index = index
	e.pressed = pressed
	e.position = pos
	e.global_position = pos
	rig._unhandled_input(e)


func _move(rig: Node2D, pos: Vector2) -> void:
	var e := InputEventMouseMotion.new()
	e.position = pos
	e.global_position = pos
	rig._unhandled_input(e)


func _button_rect(rig: Node2D, id: String) -> Rect2:
	for b in rig._buttons():
		if b["id"] == id:
			return b["rect"]
	return Rect2()


func _initialize() -> void:
	var had_settings := FileAccess.file_exists(SETTINGS)
	I18n.lang = "ru"
	var rig := _new_rig()
	await process_frame

	print("Физика")
	rig.tank_level_cm = 8.0
	rig.outlet_level_cm = 0.0
	rig.levels.fill(0.0)
	_run(rig, 60 * rig._tau())
	var err := 0.0
	for i in 5:
		err = maxf(err, absf(rig.levels[i] - 8.0 * (5 - i) / 6.0))
	_check(err < 1e-3, "постоянный бак → уровни на прямой (ошибка %.6f см)" % err)
	_check(is_equal_approx(rig._tau(), 2.0 * rig.pair_half_time_s / log(2.0)), "τ = 2·t½ / ln 2")
	rig.levels.fill(rig.vessel_height_cm)
	rig.tank_level_cm = rig.vessel_height_cm
	rig.outlet_level_cm = rig.vessel_height_cm
	_run(rig, 5 * rig._tau())
	var in_range := true
	for h in rig.levels:
		in_range = in_range and h >= 0.0 and h <= rig.vessel_height_cm
	_check(in_range, "уровни не выходят за [0, высота шкалы]")
	_check(is_equal_approx(rig.vessel_height_cm, rig.syringe_volume_ml / rig._area_cm2()), "высота шкалы = объём / площадь")

	print("Приток (тепло твердения)")
	# Постоянный приток q, бак и слив на 0 → стационар h_i = q·τ·i·(N+1−i)/2.
	rig.tank_level_cm = 0.0
	rig.outlet_level_cm = 0.0
	rig.inflow_cm_per_min = 1.0
	rig.inflow_decay_min = 0.0
	rig.levels.fill(0.0)
	var tau: float = rig._tau()
	var dt := tau * 0.05
	var t := 0.0
	while t < 40 * tau:
		rig._step(dt, tau, rig._inflow_cm_per_s(t))
		t += dt
	var q := 1.0 / 60.0
	var src_err := 0.0
	for i in 5:
		src_err = maxf(src_err, absf(rig.levels[i] - q * tau * (i + 1) * (5 - i) / 2.0))
	_check(src_err < 1e-3, "стационар с притоком = q·τ·i·(N+1−i)/2 (ошибка %.6f см)" % src_err)
	rig.inflow_decay_min = 2.0
	_check(is_equal_approx(rig._inflow_cm_per_s(120.0) / rig._inflow_cm_per_s(0.0), exp(-1.0)),
			"затухание притока: q(T) = q0 / e")
	rig.inflow_cm_per_min = 0.0
	rig.inflow_decay_min = 0.0
	for k in 12:
		rig._press_button("in_more")
	_check(is_equal_approx(rig.inflow_cm_per_min * rig._area_cm2(), 6.0), "«+ приток» ×12 → 6 мл/мин")
	for k in 20:
		rig._press_button("in_less")
	_check(rig.inflow_cm_per_min == 0.0, "«− приток» не уходит ниже нуля")
	var drops: float = 6.0 * rig.drops_per_ml
	_check(is_equal_approx(drops, 120.0), "6 мл/мин = 120 кап/мин при 20 кап/мл")

	print("Мышь")
	rig._reset()
	rig.paused = false
	rig.sim_speed = 1.0
	rig.tank_level_cm = 8.0
	rig.outlet_level_cm = 0.0
	var p: Vector2 = rig._tank_rect().get_center()
	var up := Vector2(0, 2.0 * rig.S_PX_PER_CM)
	_click(rig, p)
	_move(rig, p - up)
	_click(rig, p - up, MOUSE_BUTTON_LEFT, false)
	_check(is_equal_approx(rig.tank_level_cm, 10.0), "перетаскивание бака на 2 см (%.1f)" % rig.tank_level_cm)
	_click(rig, _button_rect(rig, "pause").get_center())
	_check(rig.paused, "кнопка «Пауза»")
	var sr: Rect2 = rig._syringe_rect(2)
	_click(rig, Vector2(sr.get_center().x, rig._sy(4.0)))
	_click(rig, Vector2(sr.get_center().x, rig._sy(4.0)), MOUSE_BUTTON_LEFT, false)
	_check(is_equal_approx(rig.levels[2], 4.0), "уровень шприца №3 под курсор")
	for i in 3:
		_click(rig, rig._outlet_end(), MOUSE_BUTTON_WHEEL_UP)
	_check(is_equal_approx(rig.outlet_level_cm, 0.3), "колесо над сливом +0,1 ×3")
	_click(rig, _button_rect(rig, "faster").get_center())
	_check(is_equal_approx(rig.sim_speed, 2.0), "кнопка «+ скорость»")

	print("Язык и инструкция")
	rig._set_help(true)
	var ru_pages: int = rig._help_pages.size()
	rig._set_help(false)
	_click(rig, _button_rect(rig, "lang").get_center())
	_check(I18n.current() == "en", "кнопка языка переключает на en")
	_check(rig._buttons()[0]["text"] in ["Pause", "Run"], "кнопки на английском")
	rig._set_help(true)
	var en_pages: int = rig._help_pages.size()
	rig._set_help(false)
	_check(ru_pages > 0 and en_pages > 0, "страницы инструкции есть: ru %d, en %d" % [ru_pages, en_pages])
	var missing := PackedStringArray()
	for key in I18n.EN:
		if str(I18n.EN[key]).is_empty():
			missing.append(key)
	_check(missing.is_empty(), "у всех ключей есть английский перевод")
	_check(FileAccess.file_exists("res://docs/instruction_ru.pdf") and FileAccess.file_exists("res://docs/instruction_en.pdf"),
			"PDF инструкции на обоих языках в docs/")

	print("CSV")
	_check(rig._save_csv(), "сохранение CSV")
	var csv := FileAccess.get_file_as_string("user://lukyanov_levels.csv")
	_check(csv.begins_with("t_s,tank_cm,h1_cm,h2_cm,h3_cm,h4_cm,h5_cm\n"), "заголовок CSV не изменился")

	# Тест не должен оставлять после себя выбранный язык.
	if not had_settings and FileAccess.file_exists(SETTINGS):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SETTINGS))

	print("Итого: %d прошло, %d провалено" % [_passed, _failed])
	quit(1 if _failed > 0 else 0)

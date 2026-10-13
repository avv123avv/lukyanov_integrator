"""Собирает инструкцию на двух языках: docs/instruction_ru.pdf и docs/instruction_en.pdf,
и рендерит страницы в docs/pages/<lang>/page_N.png для просмотра внутри Godot (F1).

Запуск:  python docs/build_instruction.py
Нужно:   pip install reportlab pypdfium2
Картинка на титуле — docs/scheme_<lang>.png (скриншот программы на этом языке).
"""
import math
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, Image, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

DOCS = Path(__file__).resolve().parent
LANGS = ("ru", "en")
# Высота картинки страницы = высота окна Godot минус поля, чтобы показывать 1:1.
PAGE_PX_HEIGHT = 1054
# Множитель всех размеров шрифта.
FONT_K = 2.0

# Параметры по умолчанию — те же, что в syringe_rig.gd.
VOLUME_ML = 60.0
INNER_D_MM = 26.7
TUBE_D_MM = 3.0
TUBE_L_CM = 30.0
HALF_TIME_S = 20.0
N = 5

AREA = math.pi * (INNER_D_MM / 20) ** 2
SCALE_CM = VOLUME_ML / AREA
TAU = 2 * HALF_TIME_S / math.log(2)
_G = math.pi * (TUBE_D_MM / 20) ** 4 * 981 / (8 * 0.01 * TUBE_L_CM)
OPEN_HALF_S = AREA / _G * math.log(2) / 2

FONTS = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Arial", str(FONTS / "arial.ttf")))
pdfmetrics.registerFont(TTFont("Arial-Bold", str(FONTS / "arialbd.ttf")))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold")

INK = colors.HexColor("#1f2328")
ACCENT = colors.HexColor("#2f6db5")
SOFT = colors.HexColor("#eef3f9")
LINE = colors.HexColor("#b8c4d2")

body = ParagraphStyle("body", fontName="Arial", fontSize=12 * FONT_K, leading=16 * FONT_K, textColor=INK, spaceAfter=5 * FONT_K)
small = ParagraphStyle("small", parent=body, fontSize=10.5 * FONT_K, leading=13.5 * FONT_K)
cell = ParagraphStyle("cell", parent=body, fontSize=11 * FONT_K, leading=14 * FONT_K, spaceAfter=0)
cell_b = ParagraphStyle("cell_b", parent=cell, fontName="Arial-Bold")
h1 = ParagraphStyle("h1", parent=body, fontName="Arial-Bold", fontSize=20 * FONT_K, leading=24 * FONT_K, textColor=ACCENT, spaceAfter=8 * FONT_K, keepWithNext=1)
h2 = ParagraphStyle("h2", parent=body, fontName="Arial-Bold", fontSize=14 * FONT_K, leading=18 * FONT_K, textColor=ACCENT, spaceBefore=6 * FONT_K, spaceAfter=4 * FONT_K, keepWithNext=1)
title = ParagraphStyle("title", parent=h1, fontSize=26 * FONT_K, leading=31 * FONT_K, alignment=TA_CENTER, spaceAfter=4 * FONT_K)
subtitle = ParagraphStyle("subtitle", parent=body, fontSize=14 * FONT_K, leading=18 * FONT_K, alignment=TA_CENTER, textColor=colors.HexColor("#555"))
caption = ParagraphStyle("caption", parent=small, alignment=TA_CENTER, textColor=colors.HexColor("#555"))

# Текущий язык сборки; меняется в main.
LANG = "ru"


def L(ru: str, en: str) -> str:
	return ru if LANG == "ru" else en


def f(x: float, d: int = 1) -> str:
	"""Число с d знаками: в русском — десятичная запятая."""
	s = f"{x:.{d}f}"
	return s.replace(".", ",") if LANG == "ru" else s


def p(text: str, style=body) -> Paragraph:
	return Paragraph(text, style)


def table(rows: list[list[str]], widths_mm: list[float]) -> Table:
	data = [[p(c, cell_b if r == 0 else cell) for c in row] for r, row in enumerate(rows)]
	t = Table(data, colWidths=[w * mm for w in widths_mm], repeatRows=1)
	t.setStyle(TableStyle([
		("BACKGROUND", (0, 0), (-1, 0), SOFT),
		("LINEBELOW", (0, 0), (-1, 0), 1, ACCENT),
		("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE),
		("VALIGN", (0, 0), (-1, -1), "TOP"),
		("TOPPADDING", (0, 0), (-1, -1), 3),
		("BOTTOMPADDING", (0, 0), (-1, -1), 4),
	]))
	return t


def steps(items: list[str]) -> list[Paragraph]:
	return [p(f"<b>{i}.</b> {t}", ParagraphStyle(f"s{i}", parent=body, leftIndent=16 * FONT_K, firstLineIndent=-16 * FONT_K))
			for i, t in enumerate(items, 1)]


# --- Модель для задач справки (тот же явный Эйлер, что в программе) --------

def simulate(h0: list[float], tank: float, drain: float, t_end: float) -> list[tuple[float, list[float]]]:
	h = list(h0)
	n = len(h)
	dt = TAU / 50
	t = 0.0
	hist = [(t, h[:])]
	while t < t_end:
		h = [min(max(h[i] + dt / TAU * ((tank if i == 0 else h[i - 1]) - 2 * h[i]
										+ (drain if i == n - 1 else h[i + 1])), 0.0), SCALE_CM)
			 for i in range(n)]
		t += dt
		hist.append((t, h[:]))
	return hist


def crossing(hist: list[tuple[float, list[float]]], i: int, level: float) -> float | None:
	"""Первый момент, когда уровень в шприце i пересёк level; None — не пересёк."""
	above = hist[0][1][i] > level
	for t, h in hist:
		if (h[i] > level) != above:
			return t
	return None


def fmt_rig(sec: float) -> str:
	m, s = divmod(round(sec), 60)
	if m:
		return L(f"{m} мин {s} с", f"{m} min {s} s")
	return L(f"{s} с", f"{s} s")


def fmt_real(sec: float) -> str:
	h = sec / 3600
	if h < 48:
		return f(h) + L(" ч", " h")
	d = h / 24
	if d < 90:
		return f(d, 0) + L(" сут", " days")
	return f(d / 30.4, 0) + L(" мес", " months")


class Case:
	"""Пересчёт реальной задачи в уровни и секунды установки."""

	def __init__(self, length_m: float, a: float, t_lo: float, t_hi: float) -> None:
		self.dx = length_m / (N + 1)
		self.tau_body = self.dx ** 2 / a
		self.m = self.tau_body / TAU
		self.t_lo, self.t_hi = t_lo, t_hi

	def lvl(self, temp: float) -> float:
		return (temp - self.t_lo) * 10.0 / (self.t_hi - self.t_lo)

	def deg_per_cm(self) -> float:
		return (self.t_hi - self.t_lo) / 10.0


def case_flow(title_: str, task: str, setup: list[list[str]], solution: list[str]) -> list:
	out = [PageBreak(), p(title_, h2), p(L("<b>Постановка.</b> ", "<b>Problem.</b> ") + task),
		   table([[L("Величина", "Quantity"), L("Расчёт", "Calculation"), L("На установке", "On the rig")]] + setup,
				 [52, 110, 105]), Spacer(1, 2 * mm)]
	out += [p((L("<b>Решение.</b> ", "<b>Solution.</b> ") if i == 0 else "") + t) for i, t in enumerate(solution)]
	return out


def history_cases() -> list:
	ml = lambda h: f"{h * AREA:.0f} " + L("мл", "ml")
	cm = L("см", "cm")
	s: list = [
		CondPageBreak(90 * mm),
		p(L("Задачи по областям: от реальной ситуации к настройке установки",
			"Problems by field: from a real situation to the rig settings"), h2),
		p(L("Во всех задачах — один и тот же порядок из раздела 5: Δx = L / 6, τ<sub>тела</sub> = Δx² / a, "
			f"M = τ<sub>тела</sub> / {f(TAU)} с, температуры укладываются в 0–10 см. Время «на установке» и "
			"результаты посчитаны той же моделью, что в программе.",
			"Every problem follows the procedure of section 5: Δx = L / 6, τ<sub>body</sub> = Δx² / a, "
			f"M = τ<sub>body</sub> / {f(TAU)} s, temperatures are mapped to 0–10 cm. Rig times and results "
			"are computed with the same model as the program.")),
		p(L("<b>Правило границ.</b> Слив умеет только забирать воду, поэтому <b>холодную</b> (нижнюю) границу "
			"ставьте на слив, а <b>тёплую</b> — на бак. Бутылка-бак может и отдавать, и принимать воду.",
			"<b>Boundary rule.</b> The drain can only take water away, so put the <b>cold</b> (lower) boundary "
			"on the drain and the <b>warm</b> one on the tank. The tank bottle can both give and take water.")),
	]

	# 1. Бетон зимой
	c = Case(0.40, 7e-7, -15, 15)
	h0 = c.lvl(15)
	hist = simulate([h0] * N, c.lvl(-15), c.lvl(-15), 40 * TAU)
	t_surf = crossing(hist, 0, c.lvl(0))
	t_mid = crossing(hist, 2, c.lvl(0))
	s += case_flow(
		L("Задача 1. Бетонирование зимой", "Problem 1. Concreting in winter"),
		L("Монолитная стена 40 см залита бетоном с температурой +15 °C (подогретая смесь). Опалубку сняли, "
		  "на улице −15 °C с обеих сторон. Через сколько часов бетон начнёт замерзать у поверхности и в середине? "
		  "Нужен ли тепляк?",
		  "A 40 cm monolithic wall is cast with concrete at +15 °C (heated mix). The formwork is removed, "
		  "it is −15 °C outside on both sides. How many hours until the concrete starts freezing near the surface "
		  "and in the middle? Is a heated enclosure needed?"),
		[
			[L("Слои", "Layers"), L("Δx = 0,40 м / 6", "Δx = 0.40 m / 6"), f"{f(c.dx * 100)} {cm}" + L(" на шприц", " per syringe")],
			[L("Время", "Time"), f"τ = {f(c.dx, 3)}² / 7·10<super>−7</super> = {f(c.tau_body / 3600)}" + L(" ч", " h"),
			 f"M ≈ {f(c.m, 0)}: " + L("1 мин", "1 min") + f" ≈ {fmt_real(60 * c.m)}"],
			[L("Температура", "Temperature"), L("−15…+15 °C на 10 см", "−15…+15 °C over 10 cm"),
			 f"1 {cm} = {f(c.deg_per_cm())} °C; 0 °C = {f(c.lvl(0))} {cm}"],
			[L("Начало", "Start"), L("Весь бетон +15 °C", "All concrete at +15 °C"),
			 L("все шприцы", "all syringes") + f" {f(h0)} {cm} ({ml(h0)})"],
			[L("Бак и слив", "Tank and drain"), L("Обе грани −15 °C", "Both faces −15 °C"), L("бак 0 см, слив 0 см", "tank 0 cm, drain 0 cm")],
			[L("Ищем", "Find"), L("Когда слой уйдёт ниже 0 °C", "When a layer drops below 0 °C"),
			 L("уровень упадёт до", "level falls to") + f" {f(c.lvl(0))} {cm} ({ml(c.lvl(0))})"],
		],
		[
			L(f"Шприц №1 (слой в {f(c.dx * 100)} см от грани) опускается до {f(c.lvl(0))} см через "
			  f"{fmt_rig(t_surf)} на установке — это ≈ <b>{fmt_real(t_surf * c.m)}</b>. Середина (№3) — через "
			  f"{fmt_rig(t_mid)}, ≈ <b>{fmt_real(t_mid * c.m)}</b>.",
			  f"Syringe #1 (the layer {f(c.dx * 100)} cm from the face) falls to {f(c.lvl(0))} cm after "
			  f"{fmt_rig(t_surf)} on the rig — that is ≈ <b>{fmt_real(t_surf * c.m)}</b>. The middle (#3) — after "
			  f"{fmt_rig(t_mid)}, ≈ <b>{fmt_real(t_mid * c.m)}</b>."),
			L("Бетон нельзя замораживать, пока он не набрал критическую прочность, а на это обычно уходят "
			  "сутки и больше. Значит, без защиты стена замёрзнет раньше времени.",
			  "Concrete must not freeze before it reaches its critical strength, which usually takes a day "
			  "or more. So without protection the wall freezes too early."),
			L(f"<b>Вариант с тепляком</b> (воздух вокруг +5 °C): бак и слив на {f(c.lvl(5))} см. Уровни не "
			  "опускаются ниже этой отметки, то есть ни один слой не уходит в минус — тепляк решает задачу. "
			  "Именно такой перебор вариантов и был главной работой интегратора.",
			  f"<b>With a heated enclosure</b> (air around +5 °C): tank and drain at {f(c.lvl(5))} cm. Levels never "
			  "fall below that mark, so no layer goes below zero — the enclosure solves the problem. "
			  "Trying out variants like this was the integrator's main job."),
		],
	)

	# 2. Вечная мерзлота
	c = Case(6.0, 5e-7, -5, 12)
	hist = simulate([c.lvl(-5)] * N, c.lvl(12), c.lvl(-5), 60 * TAU)
	thaw = [crossing(hist, i, c.lvl(0)) for i in range(4)]
	depth_inf = 6.0 * (1 - c.lvl(0) / 10.0)
	rows = "; ".join(f"{i + 1} " + L("м", "m") + f" — {fmt_real(t * c.m)}" for i, t in enumerate(thaw) if t is not None)
	s += case_flow(
		L("Задача 2. Здание на вечной мерзлоте", "Problem 2. A building on permafrost"),
		L("Отапливаемое здание стоит прямо на грунте: под полом +12 °C. Мерзлота −5 °C; на глубине 6 м её "
		  "температура не меняется. Как быстро и на какую глубину оттает грунт под зданием?",
		  "A heated building stands directly on the ground: +12 °C under the floor. Permafrost is −5 °C; at 6 m "
		  "depth its temperature does not change. How fast and how deep will the ground under the building thaw?"),
		[
			[L("Слои", "Layers"), L("Δx = 6 м / 6", "Δx = 6 m / 6"), L("1 м: №1 — глубина 1 м, …", "1 m: #1 — depth 1 m, …")],
			[L("Время", "Time"), f"τ = 1² / 5·10<super>−7</super> = {f(c.tau_body / 86400, 0)}" + L(" сут", " days"),
			 f"M ≈ {f(c.m, 0)}: " + L("1 мин", "1 min") + f" ≈ {fmt_real(60 * c.m)}"],
			[L("Температура", "Temperature"), L("−5…+12 °C на 10 см", "−5…+12 °C over 10 cm"),
			 f"1 {cm} = {f(c.deg_per_cm())} °C; 0 °C = {f(c.lvl(0), 2)} {cm}"],
			[L("Начало", "Start"), L("Весь грунт −5 °C", "All ground at −5 °C"), L("все шприцы 0 см (пустые)", "all syringes 0 cm (empty)")],
			[L("Бак / слив", "Tank / drain"), L("Пол +12 °C / на 6 м −5 °C", "Floor +12 °C / at 6 m −5 °C"),
			 L("бак 10 см, слив 0 см", "tank 10 cm, drain 0 cm")],
			[L("Ищем", "Find"), L("Когда слой оттает (выше 0 °C)", "When a layer thaws (above 0 °C)"),
			 L("уровень поднимется выше", "level rises above") + f" {f(c.lvl(0), 2)} {cm}"],
		],
		[
			L(f"Оттаивание доходит до глубины: {rows}.", f"The thaw reaches depth: {rows}."),
			L(f"В установившемся режиме уровни лягут на прямую от 10 см до 0, и граница 0 °C остановится на "
			  f"глубине ≈ <b>{f(depth_inf)} м</b>. Грунт, оттаяв, просядет — здание поведёт.",
			  f"In steady state the levels form a straight line from 10 cm to 0, and the 0 °C boundary stops at "
			  f"a depth of ≈ <b>{f(depth_inf)} m</b>. Thawed ground settles — the building will deform."),
			L(f"<b>Вариант с проветриваемым подпольем</b>: под полом зимой и летом в среднем около −2 °C, бак на "
			  f"{f(c.lvl(-2), 2)} см — ниже отметки 0 °C. Оттаивания нет. Поэтому на севере дома ставят на сваи "
			  "с продуваемым подпольем.",
			  f"<b>With a ventilated crawl space</b>: about −2 °C under the floor on average over the year, tank at "
			  f"{f(c.lvl(-2), 2)} cm — below the 0 °C mark. No thaw. That is why northern houses stand on piles "
			  "with a ventilated space underneath."),
			L("Модель не учитывает теплоту таяния льда, поэтому реальное оттаивание идёт медленнее — "
			  "для проектирования это оценка с запасом.",
			  "The model ignores the latent heat of melting ice, so real thawing is slower — "
			  "for design purposes this is a conservative estimate."),
		],
	)

	# 3. Замораживание грунта при проходке шахты
	c = Case(3.0, 5e-7, -25, 8)
	hist = simulate([c.lvl(8)] * N, c.lvl(8), c.lvl(-25), 60 * TAU)
	walls = []
	for k in range(1, 5):
		t = crossing(hist, N - k, c.lvl(0))
		if t is not None:
			walls.append(f"{f(k * c.dx)} " + L("м", "m") + f" — {fmt_real(t * c.m)}")
	wall_inf = 3.0 * c.lvl(0) / 10.0
	s += case_flow(
		L("Задача 3. Ледяная стена вокруг шахтного ствола", "Problem 3. An ice wall around a mine shaft"),
		L("Ствол шахты проходят через водоносный грунт +8 °C. Вокруг ствола бурят скважины и гонят по ним "
		  "рассол −25 °C, чтобы грунт замёрз и вода не прорвалась. За сколько суток ледяная стена станет "
		  "толщиной 1 м? До какой толщины она дорастёт?",
		  "A mine shaft is sunk through water-bearing ground at +8 °C. Boreholes around the shaft carry "
		  "−25 °C brine so the ground freezes and water cannot break through. How many days until the ice wall "
		  "is 1 m thick? How thick will it eventually get?"),
		[
			[L("Слои", "Layers"), L("Δx = 3 м / 6", "Δx = 3 m / 6"),
			 f"{f(c.dx)} " + L("м на шприц, №5 у скважин", "m per syringe, #5 next to the boreholes")],
			[L("Время", "Time"), f"τ = {f(c.dx)}² / 5·10<super>−7</super> = {f(c.tau_body / 86400, 1)}" + L(" сут", " days"),
			 f"M ≈ {f(c.m, 0)}: " + L("1 мин", "1 min") + f" ≈ {fmt_real(60 * c.m)}"],
			[L("Температура", "Temperature"), L("−25…+8 °C на 10 см", "−25…+8 °C over 10 cm"),
			 f"1 {cm} = {f(c.deg_per_cm())} °C; 0 °C = {f(c.lvl(0), 2)} {cm}"],
			[L("Начало", "Start"), L("Весь грунт +8 °C", "All ground at +8 °C"), L("все шприцы", "all syringes") + f" 10 {cm} ({ml(10)})"],
			[L("Бак / слив", "Tank / drain"), L("Грунт +8 °C / рассол −25 °C", "Ground +8 °C / brine −25 °C"),
			 L("бак 10 см, слив 0 см", "tank 10 cm, drain 0 cm")],
			[L("Ищем", "Find"), L("Когда слой замёрзнет", "When a layer freezes"), L("уровень ниже", "level below") + f" {f(c.lvl(0), 2)} {cm}"],
		],
		[
			L(f"Промерзание от скважин: {'; '.join(walls)}.", f"Freezing from the boreholes: {'; '.join(walls)}."),
			L(f"Стена толщиной 1 м — это момент, когда шприц №4 опустится ниже {f(c.lvl(0), 2)} см. "
			  f"Предельная толщина — ≈ <b>{f(wall_inf)} м</b> (там прямая от 0 до 10 см пересекает отметку 0 °C).",
			  f"A 1 m wall is the moment syringe #4 drops below {f(c.lvl(0), 2)} cm. "
			  f"The limit thickness is ≈ <b>{f(wall_inf)} m</b> (where the 0–10 cm straight line crosses the 0 °C mark)."),
			L("Вода при замерзании отдаёт много тепла, а модель этого не учитывает. Реально стена растёт "
			  "медленнее, и такой расчёт — нижняя граница сроков.",
			  "Freezing water releases a lot of heat, which the model ignores. The real wall grows "
			  "more slowly, so these times are a lower bound."),
		],
	)

	# 4. Металлургия
	c = Case(0.30, 1.4e-5, 20, 820)
	h0 = c.lvl(800)
	hist = simulate([h0] * N, c.lvl(20), c.lvl(20), 40 * TAU)
	t_surf = crossing(hist, 0, c.lvl(200))
	t_mid = crossing(hist, 2, c.lvl(200))
	mins = L(" мин", " min")
	s += case_flow(
		L("Задача 4. Закалка стальной плиты", "Problem 4. Quenching a steel slab"),
		L("Плиту толщиной 30 см, нагретую до 800 °C, опускают в воду 20 °C. Когда середина остынет ниже "
		  "200 °C и плиту можно вынимать?",
		  "A 30 cm slab heated to 800 °C is dropped into 20 °C water. When does the middle cool below "
		  "200 °C so the slab can be taken out?"),
		[
			[L("Слои", "Layers"), L("Δx = 0,30 м / 6", "Δx = 0.30 m / 6"), f"{f(c.dx * 100)} {cm}" + L(" на шприц", " per syringe")],
			[L("Время", "Time"), f"τ = {f(c.dx, 2)}² / " + L("1,4", "1.4") + f"·10<super>−5</super> = {f(c.tau_body, 0)}" + L(" с", " s"),
			 f"M ≈ {f(c.m)}: " + L("1 мин", "1 min") + f" ≈ {f(c.m)}{mins}"],
			[L("Температура", "Temperature"), L("20…820 °C на 10 см", "20…820 °C over 10 cm"),
			 f"1 {cm} = {f(c.deg_per_cm(), 0)} °C; 200 °C = {f(c.lvl(200), 2)} {cm}"],
			[L("Начало", "Start"), L("Плита 800 °C", "Slab at 800 °C"), L("все шприцы", "all syringes") + f" {f(h0, 2)} {cm} ({ml(h0)})"],
			[L("Бак и слив", "Tank and drain"), L("Обе грани в воде 20 °C", "Both faces in 20 °C water"), L("бак 0 см, слив 0 см", "tank 0 cm, drain 0 cm")],
			[L("Ищем", "Find"), L("Середина ниже 200 °C", "Middle below 200 °C"), L("шприц №3 ниже", "syringe #3 below") + f" {f(c.lvl(200), 2)} {cm}"],
		],
		[
			L(f"Слой в 5 см от грани (№1) остывает до 200 °C через {fmt_rig(t_surf)} на установке — "
			  f"≈ <b>{f(t_surf * c.m / 60)} мин</b>; середина (№3) — через {fmt_rig(t_mid)}, "
			  f"≈ <b>{f(t_mid * c.m / 60)} мин</b>.",
			  f"The layer 5 cm from the face (#1) cools to 200 °C after {fmt_rig(t_surf)} on the rig — "
			  f"≈ <b>{f(t_surf * c.m / 60)} min</b>; the middle (#3) — after {fmt_rig(t_mid)}, "
			  f"≈ <b>{f(t_mid * c.m / 60)} min</b>."),
			L("Здесь масштаб времени около 3: установка работает лишь втрое быстрее реальности. Это нормально — "
			  "интегратор выбирают не ради скорости, а ради наглядности и перебора вариантов.",
			  "The time scale here is about 3: the rig runs only three times faster than reality. That is fine — "
			  "the integrator is chosen for clarity and for trying variants, not for speed."),
			L("Поверхность считается сразу равной температуре воды; на деле вокруг горячей стали сначала "
			  "образуется паровая рубашка, и первые минуты остывание идёт медленнее.",
			  "The surface is assumed to be at water temperature right away; in reality a vapour blanket "
			  "first forms around hot steel, and cooling is slower for the first minutes."),
		],
	)
	return s


def footer(canvas, doc) -> None:
	canvas.saveState()
	canvas.setFont("Arial", 9 * FONT_K)
	canvas.setFillColor(colors.HexColor("#777"))
	w, _ = landscape(A4)
	canvas.drawString(15 * mm, 8 * mm, L("Интегратор Лукьянова из шприцев и капельниц — инструкция",
										 "Lukyanov integrator from syringes and IV drips — manual"))
	canvas.drawRightString(w - 15 * mm, 8 * mm, L("стр. ", "p. ") + str(doc.page))
	canvas.restoreState()


def story() -> list:
	s: list = []
	cm = L("см", "cm")
	ml = L("мл", "ml")

	# --- Титул -------------------------------------------------------------
	s += [
		Spacer(1, 4 * mm),
		p(L("Гидравлический интегратор Лукьянова<br/>из шприцев и капельниц",
			"Lukyanov hydraulic integrator<br/>from syringes and IV drips"), title),
		p(L("Инструкция по сборке, калибровке и расчётам", "Assembly, calibration and calculation manual"), subtitle),
		Spacer(1, 5 * mm),
		Image(str(DOCS / f"scheme_{LANG}.png"), width=100 * mm, height=100 * mm * 1080 / 1920),
		p(L("Схема в программе. F1 — открыть/закрыть эту инструкцию, ← / → — листать страницы.",
			"The scheme in the program. F1 opens/closes this manual, ← / → flip pages."), caption),
		PageBreak(),
	]

	# --- 1. Принцип --------------------------------------------------------
	s += [
		p(L("1. Что это и как работает", "1. What it is and how it works"), h1),
		p(L("В 1936 году В. С. Лукьянов заметил, что вода, перетекающая между сосудами через узкие трубки, "
			"подчиняется тому же уравнению, что и тепло, перетекающее между слоями тела. Если разбить тело на "
			"слои и каждому слою поставить в соответствие сосуд, то уровни воды будут повторять температуры "
			"слоёв — установка «решает» уравнение теплопроводности сама, без формул.",
			"In 1936 V. S. Lukyanov noticed that water flowing between vessels through narrow tubes obeys the "
			"same equation as heat flowing between layers of a body. Split the body into layers, give each layer "
			"a vessel, and the water levels follow the layer temperatures — the rig “solves” the heat equation "
			"by itself, without formulas.")),
		p(L("Каждый шприц подчиняется уравнению", "Each syringe obeys") + "  dh<sub>i</sub>/dt = (h<sub>i−1</sub> − 2h<sub>i</sub> + "
		  "h<sub>i+1</sub>) / τ,  " + L("где τ — постоянная времени ячейки, которую задают роликовые зажимы.",
										"where τ is the cell time constant set by the roller clamps.")),
		Spacer(1, 2 * mm),
		table([
			[L("Тепловая задача", "Heat problem"), L("Установка", "Rig")],
			[L("Температура слоя", "Layer temperature"), L("Уровень воды в шприце (см от нулевой отметки)", "Water level in a syringe (cm above the zero mark)")],
			[L("Теплоёмкость слоя", "Layer heat capacity"), L("Площадь сечения шприца", "Syringe cross-section area")],
			[L("Термическое сопротивление между слоями", "Thermal resistance between layers"), L("Трубка капельницы с роликовым зажимом", "IV tube with a roller clamp")],
			[L("Температура среды слева", "Ambient temperature, left"), L("Уровень воды в баке (бутылка на штативе)", "Water level in the tank (bottle on a stand)")],
			[L("Температура среды справа", "Ambient temperature, right"), L("Высота конца сливной трубки", "Height of the drain tube end")],
			[L("Время", "Time"), L("Время, в своём масштабе (см. раздел 5)", "Time, at its own scale (see section 5)")],
		], [110, 157]),
		Spacer(1, 4 * mm),
		p(L("Главная проверка исправности: если держать бак на постоянном уровне, через некоторое время уровни "
			"в шприцах выстраиваются на прямую линию от бака к сливу. Программа рисует эту линию пунктиром.",
			"The main health check: keep the tank at a constant level, and after a while the syringe levels "
			"line up on a straight line from the tank to the drain. The program draws this line dashed.")),
		CondPageBreak(70 * mm),
	]

	# --- 2. Детали ---------------------------------------------------------
	s += [
		p(L(f"2. Детали (на {N} шприцев)", f"2. Parts (for {N} syringes)"), h1),
		table([
			["№" if LANG == "ru" else "#", L("Деталь", "Part"), L("Кол-во", "Qty"), L("Примечание", "Notes")],
			["1", L("Пластиковая бутылка 0,5–1 л", "Plastic bottle 0.5–1 L"), "1", L("Дно отрезать; висит горлышком вниз — это бак", "Cut off the bottom; hangs neck down — this is the tank")],
			["2", L(f"Шприц {f(VOLUME_ML, 0)} мл", f"Syringe {f(VOLUME_ML, 0)} ml"), str(N),
			 L(f"Внутренний Ø ≈ {f(INNER_D_MM)} мм, шкала {f(VOLUME_ML, 0)} мл ≈ {f(SCALE_CM)} см. Поршни не нужны",
			   f"Inner Ø ≈ {f(INNER_D_MM)} mm, {f(VOLUME_ML, 0)} ml scale ≈ {f(SCALE_CM)} cm. Plungers not needed")],
			["3", L("Трёхходовой краник (Luer)", "3-way stopcock (Luer)"), str(N), L("Продаётся в аптеках; по одному под каждым шприцем", "Sold in pharmacies; one under each syringe")],
			["4", L("Система-капельница", "IV drip set"), str(N + 1), L("Нужны трубка и роликовый зажим; камера и игла не нужны", "Only the tube and roller clamp are used; no drip chamber or needle")],
			["5", L("Роликовый зажим", "Roller clamp"), "—", L("Входит в капельницу; это регулируемое сопротивление", "Part of the drip set; it is the adjustable resistance")],
			["6", L("Стакан", "Cup"), "1", L("Под слив", "Under the drain")],
			["7", L("Штатив, рейка, прищепки или зажимы", "Stand, rail, clips or clamps"), "2", L("Держат бак (подвижный) и конец сливной трубки (неподвижный)", "Hold the tank (movable) and the drain tube end (fixed)")],
			["", L("Уровень (строительный), линейка, скотч", "Spirit level, ruler, tape"), "", L("Чтобы выставить нули шкал на одну высоту", "To set all scale zeros at the same height")],
			["", L("Пищевой краситель", "Food colouring"), "", L("Уровни лучше видны на видео", "Levels are easier to see on video")],
			["", L("Телефон на штативе", "Phone on a tripod"), "", L("Съёмка таймлапса для сравнения с программой", "Timelapse to compare with the program")],
		], [12, 92, 32, 131]),
		Spacer(1, 3 * mm),
		p(L(f"Число капельниц на одну больше числа шприцев: трубки идут бак → №1 → … → №{N} → слив, "
			f"всего {N + 1} отрезков, и на каждом свой зажим.",
			f"There is one more drip set than syringes: tubes run tank → #1 → … → #{N} → drain, "
			f"{N + 1} pieces in total, each with its own clamp."), small),
		CondPageBreak(70 * mm),
	]

	# --- 3. Сборка ---------------------------------------------------------
	s += [p(L("3. Сборка", "3. Assembly"), h1)]
	s += steps([
		L(f"<b>Капельницы.</b> Отрежьте капельную камеру и иглу. Оставьте отрезок трубки ~{f(TUBE_L_CM, 0)} см "
		  "с роликовым зажимом посередине. Все отрезки делайте одинаковой длины.",
		  f"<b>Drip sets.</b> Cut off the drip chamber and the needle. Keep a ~{f(TUBE_L_CM, 0)} cm piece of tube "
		  "with the roller clamp in the middle. Make all pieces the same length."),
		L("<b>Шприцы.</b> Выньте поршни. Закрепите шприцы на рейке вертикально, носиком вниз, "
		  "с равными промежутками. <b>Нулевые отметки шкал должны быть строго на одной высоте</b> — проверьте "
		  "уровнем или по натянутой нитке. Это самое важное условие точности.",
		  "<b>Syringes.</b> Remove the plungers. Mount the syringes on a rail vertically, nozzle down, "
		  "evenly spaced. <b>All scale zero marks must be at exactly the same height</b> — check with a spirit "
		  "level or a taut string. This matters most for accuracy."),
		L("<b>Краники.</b> Вставьте носик каждого шприца в боковой порт краника. К прямым портам подключите "
		  "трубки: надеть плотно на носик или через люэр-переходник. Рычаги поверните вниз — все три порта открыты.",
		  "<b>Stopcocks.</b> Insert each syringe nozzle into the side port of a stopcock. Connect the tubes to the "
		  "straight ports: push them on tightly or use a Luer adapter. Turn the levers down — all three ports open."),
		L("<b>Бак.</b> Отрежьте у бутылки дно, вставьте шип капельницы в пробку, подвесьте бутылку горлышком вниз "
		  "на штатив. Высота воды в бутылке над нулём шприцев — это «уровень бака».",
		  "<b>Tank.</b> Cut the bottom off the bottle, push the drip set spike into the cap, hang the bottle neck "
		  "down on a stand. The water height in the bottle above the syringe zero is the “tank level”."),
		L(f"<b>Слив.</b> Конец трубки от шприца №{N} закрепите на втором штативе на нужной высоте над стаканом. "
		  "Высота конца трубки над нулём — это «уровень слива».",
		  f"<b>Drain.</b> Fix the end of the tube from syringe #{N} on the second stand at the required height "
		  "above the cup. The height of the tube end above zero is the “drain level”."),
		L("<b>Заполнение.</b> Залейте подкрашенную воду через бак, закрыв слив зажимом. Выгоните пузыри: постучите "
		  "по трубкам, покачайте их, наклоните краники. Пузырь в трубке резко меняет её сопротивление.",
		  "<b>Filling.</b> Pour coloured water in through the tank with the drain clamped shut. Chase out bubbles: tap "
		  "the tubes, wiggle them, tilt the stopcocks. A bubble in a tube changes its resistance sharply."),
		L("<b>Съёмка.</b> Поставьте телефон перпендикулярно рейке так, чтобы шкалы всех шприцев и бутылки были "
		  "в кадре. Включите таймлапс (интервал 1–5 с).",
		  "<b>Filming.</b> Place the phone square to the rail so that the scales of all syringes and the bottle are "
		  "in frame. Start a timelapse (1–5 s interval)."),
	])
	s += [CondPageBreak(70 * mm)]

	# --- 4. Калибровка -----------------------------------------------------
	s += [
		p(L("4. Калибровка", "4. Calibration"), h1),
		p(L(f"Все пары соседних шприцев должны иметь одинаковое <b>время полувыравнивания t½</b> — время, за которое "
			f"разница уровней в паре падает вдвое. Это и есть параметр <b>pair_half_time_s</b> в программе "
			f"(по умолчанию {f(HALF_TIME_S, 0)} с, τ = 2·t½ / ln 2 ≈ {f(TAU)} с).",
			f"All pairs of neighbouring syringes must have the same <b>half-equalisation time t½</b> — the time for the "
			f"level difference in a pair to halve. This is the <b>pair_half_time_s</b> parameter in the program "
			f"(default {f(HALF_TIME_S, 0)} s, τ = 2·t½ / ln 2 ≈ {f(TAU)} s).")),
		p(L(f"Оценка по закону Пуазейля: открытая трубка Ø{f(TUBE_D_MM, 0)} мм × {f(TUBE_L_CM, 0)} см даёт "
			f"t½ ≈ {f(OPEN_HALF_S)} с — слишком быстро для съёмки. Зажимами замедлите до 15–30 с.",
			f"Poiseuille estimate: an open Ø{f(TUBE_D_MM, 0)} mm × {f(TUBE_L_CM, 0)} cm tube gives "
			f"t½ ≈ {f(OPEN_HALF_S)} s — too fast to film. Slow it down to 15–30 s with the clamps.")),
		p(L("Рычаг краника указывает на перекрытый порт (у большинства моделей — проверьте на своих). "
			"Рычаг вниз, в сторону несуществующего порта, — открыты все три.",
			"The stopcock lever points at the closed port (on most models — check yours). "
			"Lever down, towards the missing port, means all three are open."), small),
		p(L("Порядок для пары i – (i+1)", "Procedure for pair i – (i+1)"), h2),
	]
	s += steps([
		L("Краник i: перекройте порт в сторону предыдущего шприца (или бака). Краник i+1: перекройте порт "
		  "в сторону следующего шприца (или слива). Теперь вода ходит только между i и i+1.",
		  "Stopcock i: close the port towards the previous syringe (or the tank). Stopcock i+1: close the port "
		  "towards the next syringe (or the drain). Now water flows only between i and i+1."),
		L(f"Налейте в шприц i примерно {f(VOLUME_ML * 0.7, 0)} мл, шприц i+1 опустошите (через краник).",
		  f"Fill syringe i with about {f(VOLUME_ML * 0.7, 0)} ml, empty syringe i+1 (through its stopcock)."),
		L("Запустите секундомер. Засеките момент, когда разница уровней стала вдвое меньше начальной.",
		  "Start a stopwatch. Note when the level difference has dropped to half the initial one."),
		L(f"Если t½ меньше {f(HALF_TIME_S, 0)} с — подкрутите зажим, больше — отпустите. Повторите.",
		  f"If t½ is under {f(HALF_TIME_S, 0)} s, tighten the clamp; if over, loosen it. Repeat."),
		L("Так для всех пар №1–№2 … №4–№5.", "Do this for all pairs #1–#2 … #4–#5."),
		L(f"Крайние трубки (бак–№1 и №{N}–слив): оставьте шприц соединённым только с баком (или сливом). "
		  "Его отклонение от уровня бака должно падать вдвое за <b>2·t½</b> — бутылка широкая, её уровень почти не меняется.",
		  f"End tubes (tank–#1 and #{N}–drain): leave the syringe connected only to the tank (or drain). "
		  "Its deviation from the tank level should halve in <b>2·t½</b> — the bottle is wide, so its level barely changes."),
	])
	s += [
		p(L("Проверка установки", "Rig check"), h2),
		p(L("Откройте все краники, поднимите бак, например, на 8 см, слив — на 0. Через 5–10 τ уровни должны "
			"лечь на прямую. Если линия «ломается», в этом месте трубка с другим сопротивлением: пузырь, "
			"перекрученный зажим или пережатая трубка.",
			"Open all stopcocks, raise the tank to e.g. 8 cm, drain at 0. After 5–10 τ the levels should form "
			"a straight line. If the line “bends”, the tube at that spot has a different resistance: a bubble, "
			"an over-tightened clamp or a pinched tube.")),
		CondPageBreak(70 * mm),
	]

	# --- 5. Расчёты --------------------------------------------------------
	body_ = L("тела", "body")
	rig_ = L("уст", "rig")
	s += [
		p(L("5. Как проводить расчёты", "5. How to run calculations"), h1),
		p(L("Реальная задача переводится в уровни и секунды установки, установка «считает», ответ переводится "
			"обратно. Нужны три масштаба.",
			"A real problem is converted into rig levels and seconds, the rig “computes”, and the answer is converted "
			"back. Three scales are needed.")),
		table([
			[L("Масштаб", "Scale"), L("Формула", "Formula"), L("Смысл", "Meaning")],
			[L("Длина", "Length"), f"Δx = L / (N + 1) = L / {N + 1}",
			 L("Тело толщиной L делится на N+1 интервалов; бак и слив стоят на поверхностях, шприцы — внутри",
			   "A body of thickness L is split into N+1 intervals; tank and drain sit on the surfaces, syringes inside")],
			[L("Время", "Time"), f"τ<sub>{body_}</sub> = Δx² / a;   M = τ<sub>{body_}</sub> / τ<sub>{rig_}</sub>",
			 L(f"a — температуропроводность материала, τ<sub>уст</sub> ≈ {f(TAU)} с. 1 с на установке = M с в реальности",
			   f"a is the material's thermal diffusivity, τ<sub>rig</sub> ≈ {f(TAU)} s. 1 s on the rig = M s in reality")],
			[L("Температура", "Temperature"), f"h = (T − T<sub>min</sub>) / (T<sub>max</sub> − T<sub>min</sub>) · 10 {cm}",
			 L(f"Диапазон температур укладывается в шкалу ({f(SCALE_CM)} см). 1 см уровня = {f(AREA)} мл",
			   f"The temperature range is mapped onto the scale ({f(SCALE_CM)} cm). 1 cm of level = {f(AREA)} ml")],
		], [58, 90, 119]),
		Spacer(1, 3 * mm),
		table([
			[L("Материал", "Material"), L("a, м²/с", "a, m²/s"), L("Материал", "Material"), L("a, м²/с", "a, m²/s")],
			[L("Бетон", "Concrete"), "7·10<super>−7</super>", L("Кирпич", "Brick"), "5·10<super>−7</super>"],
			[L("Дерево (сосна поперёк волокон)", "Wood (pine, across grain)"), "1·10<super>−7</super>", L("Сталь", "Steel"), L("1,4", "1.4") + "·10<super>−5</super>"],
			[L("Грунт влажный", "Moist soil"), "5·10<super>−7</super>", L("Минвата", "Mineral wool"), "1·10<super>−6</super>"],
		], [85, 45, 85, 45]),
		p(L("Порядок работы", "Procedure"), h2),
	]
	s += steps([
		L("Откалибруйте установку (раздел 4).", "Calibrate the rig (section 4)."),
		L("Переведите задачу в сантиметры и секунды установки по формулам выше.",
		  "Convert the problem into rig centimetres and seconds with the formulas above."),
		L("Начальное состояние: перекройте краники, налейте в каждый шприц нужное число мл, откройте краники.",
		  "Initial state: close the stopcocks, fill each syringe with the required ml, open the stopcocks."),
		L("Границы: поднимите бак на нужную высоту, закрепите слив на своей.",
		  "Boundaries: raise the tank to its height, fix the drain at its own."),
		L("Запустите таймлапс. Если температура среды меняется (день/ночь, нагрев по графику) — двигайте бак "
		  "по расписанию вручную. Именно такие задачи аналоговый интегратор решает лучше всего.",
		  "Start the timelapse. If the ambient temperature changes (day/night, scheduled heating), move the tank "
		  "by hand on schedule. This is exactly the kind of problem an analog integrator handles best."),
		L("Переведите показания обратно: мл → см → °C, время установки × M → реальное время.",
		  "Convert the readings back: ml → cm → °C, rig time × M → real time."),
	])
	s += [CondPageBreak(70 * mm)]

	# --- 6. Пример ---------------------------------------------------------
	a = 7e-7
	dx = 0.30 / (N + 1)
	tau_body = dx * dx / a
	m = tau_body / TAU
	# Тот же явный Эйлер, что в программе: где окажется №3 через 3 минуты установки.
	h = [10.0] * N
	dt = TAU * 0.05
	for _ in range(int(180 / dt)):
		h = [h[i] + dt / TAU * ((10.0 if i == 0 else h[i - 1]) - 2 * h[i] + (0.0 if i == N - 1 else h[i + 1]))
			 for i in range(N)]
	h3 = h[2]
	s += [
		p(L("6. Пример: бетонная стена промерзает", "6. Example: a concrete wall freezing through"), h1),
		p(L("Стена 30 см, внутри +20 °C, снаружи резко наступил мороз −20 °C. Как холод пойдёт через стену "
			"и когда установится режим?",
			"A 30 cm wall, +20 °C inside, and a sudden −20 °C frost outside. How does the cold move through the wall "
			"and when does it settle?")),
		table([
			[L("Величина", "Quantity"), L("Расчёт", "Calculation"), L("Значение", "Value")],
			["Δx", L("0,30 м", "0.30 m") + f" / {N + 1}", f"{f(dx * 100, 0)} {cm}"],
			[f"τ<sub>{body_}</sub>", f"{f(dx, 2)}² / 7·10<super>−7</super>", f"≈ {f(tau_body, 0)}" + L(" с ≈ ", " s ≈ ") + f(tau_body / 3600) + L(" ч", " h")],
			["M", f"{f(tau_body, 0)} / {f(TAU)}", f"≈ {f(m, 0)}: " + L("1 мин установки ≈ ", "1 rig min ≈ ") + f(m / 60) + L(" ч", " h")],
			[L("Температура", "Temperature"), L("40 °C на 10 см", "40 °C over 10 cm"), L("1 см = 4 °C; 0 см = −20 °C, 10 см = +20 °C", "1 cm = 4 °C; 0 cm = −20 °C, 10 cm = +20 °C")],
			[L("Начало", "Start"), L("Стена везде +20 °C", "Wall at +20 °C throughout"), L("все шприцы 10 см", "all syringes 10 cm") + f" ({f(10 * AREA, 0)} {ml})"],
			[L("Бак (помещение)", "Tank (room)"), "+20 °C", f"10 {cm}"],
			[L("Слив (улица)", "Drain (outside)"), "−20 °C", f"0 {cm}"],
		], [60, 82, 125]),
		Spacer(1, 3 * mm),
		p(L("Чтение ответа", "Reading the answer"), h2),
		p(L(f"Пусть через 3 мин установки (≈ {f(3 * m / 60)} ч реального времени) шприц №3 (середина стены) "
			f"показывает {f(h3 * AREA, 0)} мл (столько даёт программа). Тогда h = {f(h3 * AREA, 0)} / {f(AREA)} ≈ {f(h3)} см, "
			f"а температура T = −20 + {f(h3)} · 4 ≈ {f(-20 + h3 * 4, 0)} °C. "
			"Через 10–15 мин установки уровни лягут на прямую — это установившийся режим, "
			"дальше стена промерзать не будет.",
			f"Say after 3 rig minutes (≈ {f(3 * m / 60)} h of real time) syringe #3 (middle of the wall) "
			f"shows {f(h3 * AREA, 0)} ml (as the program gives). Then h = {f(h3 * AREA, 0)} / {f(AREA)} ≈ {f(h3)} cm, "
			f"and the temperature T = −20 + {f(h3)} · 4 ≈ {f(-20 + h3 * 4, 0)} °C. "
			"After 10–15 rig minutes the levels form a straight line — that is the steady state; "
			"the wall will not freeze any further.")),
		p(L("Ограничения", "Limitations"), h2),
		p(L("• Тело однородное: для слоёв из разных материалов нужны разные t½ у разных пар (программа пока так не умеет).",
			"• The body is uniform: layers of different materials need different t½ per pair (the program cannot do that yet).")),
		p(L("• Трубка бака равна обычному слою, т. е. стена считается идеально прижатой к среде. Теплообмен "
			"с воздухом (1/α) можно смоделировать, сильнее закрутив зажим бака и слива.",
			"• The tank tube equals an ordinary layer, i.e. the wall is in perfect contact with the environment. Heat "
			"exchange with air (1/α) can be modelled by tightening the tank and drain clamps more.")),
		p(L(f"• {N} слоёв дают грубый, но инженерный профиль: погрешность — единицы процентов. Больше шприцев — точнее.",
			f"• {N} layers give a coarse but usable engineering profile: error of a few percent. More syringes — more accurate.")),
		CondPageBreak(70 * mm),
	]

	# --- 7. Программа ------------------------------------------------------
	s += [
		p(L("7. Работа с программой", "7. Using the program"), h1),
		table([
			[L("Клавиша", "Key"), L("Действие", "Action"), L("Клавиша", "Key"), L("Действие", "Action")],
			["↑ / ↓", L("Бак выше / ниже на 1 см", "Tank up / down 1 cm"), "S", L("Сохранить замеры в CSV", "Save readings to CSV")],
			[L("Пробел", "Space"), L("Пауза", "Pause"), "F1", L("Эта инструкция", "This manual")],
			["+ / −", L("Скорость времени ×2 / ÷2", "Time speed ×2 / ÷2"), "← / →", L("Страницы инструкции", "Manual pages")],
			["R", L("Сброс", "Reset"), "O", L("Открыть PDF во внешней программе", "Open the PDF in an external viewer")],
			["L", L("Язык: русский / English", "Language: English / Russian"), "", ""],
		], [46, 88, 46, 87]),
		p(L("Мышь (и касания на Steam Deck)", "Mouse (and touch on Steam Deck)"), h2),
		table([
			[L("Действие", "Action"), L("Что происходит", "Effect")],
			[L("Тянуть бутылку", "Drag the bottle"), L("Бак вверх / вниз; уровень пишется над бутылкой", "Tank up / down; the level is shown above the bottle")],
			[L("Тянуть конец сливной трубки", "Drag the drain tube end"), L("Меняет уровень слива", "Changes the drain level")],
			[L("Нажать или тянуть внутри шприца", "Click or drag inside a syringe"), L("Уровень воды встаёт под курсор — так задают начальное состояние", "The water level jumps to the cursor — this is how you set the initial state")],
			[L("Колесо над баком, сливом или шприцем", "Wheel over tank, drain or syringe"), L("Точная подстройка ±0,1 см", "Fine adjustment ±0.1 cm")],
			[L("Кнопки сверху", "Top buttons"), L("Пауза/Пуск, − / + скорость, Сброс, Сохранить CSV, Инструкция, язык",
												 "Pause/Run, − / + speed, Reset, Save CSV, Manual, language")],
		], [95, 172]),
		p(L("Начальное состояние мышью: нажмите «Пауза», расставьте уровни в шприцах и бак, затем «Пуск». "
			"Так удобно повторять задачи из разделов 6 и 8.",
			"Initial state with the mouse: press “Pause”, set the syringe levels and the tank, then “Run”. "
			"Handy for reproducing the problems in sections 6 and 8."), small),
		p(L("Параметры (Inspector, узел SyringeRig)", "Parameters (Inspector, SyringeRig node)"), h2),
		table([
			[L("Параметр", "Parameter"), L("Что это", "Meaning")],
			["pair_half_time_s", L("t½ пары шприцев — из калибровки (раздел 4)", "t½ of a syringe pair — from calibration (section 4)")],
			["syringe_volume_ml, syringe_inner_d_mm", L("Объём и внутренний диаметр ваших шприцев — по ним считается высота шкалы", "Volume and inner diameter of your syringes — they set the scale height")],
			["tube_inner_d_mm, tube_length_cm", L("Трубки капельниц — для оценки t½ открытой трубки", "Drip tubes — for the open-tube t½ estimate")],
			["tank_level_cm, outlet_level_cm", L("Уровни бака и слива на старте", "Tank and drain levels at start")],
			["start_level_cm", L("Начальный уровень во всех шприцах", "Initial level in all syringes")],
			["record_interval_s", L("Как часто писать строку в CSV", "How often to write a CSV row")],
		], [95, 172]),
		p(L("Сравнение с установкой", "Comparing with the rig"), h2),
		p(L("CSV сохраняется в user://lukyanov_levels.csv (путь показывается на экране): t_s, tank_cm, h1_cm … "
			"h5_cm. Задайте в программе те же t½, бак и слив, что на установке, запустите одновременно с "
			f"таймлапсом, сохраните CSV и сравните с уровнями, снятыми с видео (мл ÷ {f(AREA)} = см). Расхождение "
			"указывает на пузыри, разные зажимы или нули шкал не на одной высоте.",
			"The CSV is saved to user://lukyanov_levels.csv (the path is shown on screen): t_s, tank_cm, h1_cm … "
			"h5_cm. Set the same t½, tank and drain in the program as on the rig, start together with the "
			f"timelapse, save the CSV and compare with levels read from the video (ml ÷ {f(AREA)} = cm). Differences "
			"point to bubbles, unequal clamps or scale zeros at different heights.")),
		CondPageBreak(70 * mm),
	]

	# --- 8. История --------------------------------------------------------
	s += [
		p(L("8. Историческая справка: как интегратор помогал стройке", "8. History: how the integrator helped builders"), h1),
		p(L("Задача", "The problem"), h2),
		p(L("В конце 1920-х инженер Владимир Сергеевич Лукьянов работал на строительстве железных дорог "
			"(в том числе линии Троицк–Орск). Бетонные сооружения трескались: бетон при твердении сам выделяет "
			"тепло, а снаружи мороз или жара, и внутри массива возникают перепады температур и напряжения.",
			"In the late 1920s engineer Vladimir Sergeyevich Lukyanov worked on railway construction "
			"(including the Troitsk–Orsk line). Concrete structures cracked: setting concrete releases heat "
			"while outside there is frost or heat, so temperature differences and stresses build up inside.")),
		p(L("Чтобы понять, где и когда появятся трещины, нужно знать, как температура меняется внутри бетона "
			"день за днём. Это уравнение теплопроводности с меняющимися условиями: погода, тепло твердения, "
			"утепление опалубки. Точно решить его на бумаге было невозможно, а приближённые ручные расчёты "
			"занимали недели и давали грубый результат.",
			"To know where and when cracks appear you need the temperature inside the concrete day by day. "
			"That is the heat equation with changing conditions: weather, heat of setting, formwork insulation. "
			"It could not be solved exactly on paper, and approximate hand calculations took weeks and were crude.")),
		p(L("Решение", "The solution"), h2),
		p(L("В 1936 году Лукьянов построил гидравлический интегратор — ровно тот принцип, что в этой установке: "
			"сосуды — слои бетона, трубки — теплопроводность, уровень воды — температура. Инженер выставлял "
			"начальные уровни, по графику двигал бак («погода снаружи») и снимал показания. Задача, на которую "
			"раньше уходили недели, решалась за часы.",
			"In 1936 Lukyanov built the hydraulic integrator — exactly the principle of this rig: "
			"vessels are concrete layers, tubes are heat conduction, water level is temperature. The engineer set "
			"initial levels, moved the tank on schedule (“the weather outside”) and took readings. A problem that "
			"used to take weeks was solved in hours.")),
		p(L("Главное преимущество — можно было быстро перебрать варианты: «а если утеплить», «а если заливать "
			"в другой месяц», «а если подогревать» — и выбрать лучший до начала работ.",
			"The main advantage was trying variants quickly: “what if we insulate”, “what if we pour "
			"in another month”, “what if we heat it” — and picking the best before work began.")),
		p(L("Где применяли", "Where it was used"), h2),
		table([
			[L("Область", "Field"), L("Что считали", "What was calculated")],
			[L("Бетонирование зимой", "Winter concreting"), L("Сколько держать опалубку и утепление, чтобы бетон не промёрз и не потрескался",
															  "How long to keep formwork and insulation so concrete neither freezes nor cracks")],
			[L("Вечная мерзлота", "Permafrost"), L("Как насыпь, здание или фундамент меняют мерзлоту под собой: начнёт ли грунт "
												   "оттаивать и проседать. Северные железные дороги, города, шахты",
												   "How an embankment, building or foundation changes the permafrost below: will the ground "
												   "thaw and settle. Northern railways, towns, mines")],
			[L("Горное дело и геология", "Mining and geology"), L("Промерзание и оттаивание пород вокруг шахт, тепловой режим недр",
																 "Freezing and thawing of rock around mines, subsurface thermal regime")],
			[L("Металлургия и другое", "Metallurgy and more"), L("Остывание слитков; фильтрация воды в грунте, диффузия — "
																 "всё, что сводится к тому же уравнению",
																 "Cooling of ingots; groundwater seepage, diffusion — "
																 "anything that reduces to the same equation")],
		], [65, 202]),
		p(L("Развитие", "Development"), h2),
		table([
			[L("Годы", "Years"), L("Событие", "Event")],
			["1936", L("Первый одномерный интегратор (как эта установка)", "First one-dimensional integrator (like this rig)")],
			["1941", L("Двумерный интегратор: сечение плотины или фундамента целиком, а не один разрез",
					   "Two-dimensional integrator: a whole dam or foundation cross-section, not a single line")],
			[L("1950-е", "1950s"), L("Серийный выпуск на Рязанском заводе счётно-аналитических машин; интеграторы работали "
									  "в десятках институтов (по разным данным — больше чем в сотне организаций), в том числе за рубежом",
									  "Series production at the Ryazan calculating-machine plant; integrators worked in dozens "
									  "of institutes (by some accounts over a hundred organisations), including abroad")],
			[L("до 1980-х", "until 1980s"), L("Работали, пока их не вытеснили цифровые ЭВМ: для таких задач гидравлическая "
											  "машина долго была нагляднее и надёжнее ранних компьютеров",
											  "In use until digital computers replaced them: for these problems the hydraulic "
											  "machine long stayed clearer and more reliable than early computers")],
		], [32, 235]),
		Spacer(1, 2 * mm),
		p(L("Два экземпляра сохранились в Политехническом музее (Москва). Точные даты и число машин в разных "
			"источниках расходятся.",
			"Two machines are preserved at the Polytechnic Museum (Moscow). Exact dates and numbers of machines "
			"differ between sources."), small),
	]
	s += history_cases()
	s += [
		CondPageBreak(60 * mm),
		p(L("Что ещё можно повторить на этой установке", "What else you can reproduce on this rig"), h2),
		p(L("• <b>Промерзание стены или грунта</b> при меняющейся погоде — уже сейчас: двигайте бак по графику "
			"наружной температуры (пример — раздел 6).",
			"• <b>Freezing of a wall or ground</b> under changing weather — already possible: move the tank following "
			"the outdoor temperature (example — section 6).")),
		p(L("• <b>Тепло твердения бетона</b> — собственный источник тепла в каждом слое — пока нет. Для этого в "
			"каждый шприц нужно медленно и равномерно доливать воду — например, отдельной капельницей. "
			"Здесь система-капельница пригодилась бы по прямому назначению.",
			"• <b>Heat of concrete setting</b> — a heat source inside each layer — not yet. That needs slowly and "
			"evenly adding water to each syringe — for example with a separate drip. "
			"Here the IV drip set would be used for its original purpose.")),
	]
	return s


def render_pages(pdf: Path, pages: Path) -> int:
	import pypdfium2 as pdfium
	pages.mkdir(parents=True, exist_ok=True)
	# Вместе с .import, иначе Godot продолжит видеть удалённые страницы.
	for old in [*pages.glob("page_*.png"), *pages.glob("page_*.png.import")]:
		old.unlink()
	doc = pdfium.PdfDocument(str(pdf))
	for i, page in enumerate(doc, 1):
		scale = PAGE_PX_HEIGHT / page.get_height()
		page.render(scale=scale).to_pil().save(pages / f"page_{i}.png")
	return len(doc)


if __name__ == "__main__":
	for LANG in LANGS:
		pdf = DOCS / f"instruction_{LANG}.pdf"
		SimpleDocTemplate(
			str(pdf), pagesize=landscape(A4),
			leftMargin=15 * mm, rightMargin=15 * mm, topMargin=12 * mm, bottomMargin=14 * mm,
			title=L("Интегратор Лукьянова из шприцев и капельниц", "Lukyanov integrator from syringes and IV drips"),
			author="lukyanov_integrator",
		).build(story(), onFirstPage=footer, onLaterPages=footer)
		n = render_pages(pdf, DOCS / "pages" / LANG)
		print(f"{LANG}: {pdf.name}, {n} pages")

"""Generate PythonForNinjaTrader.pdf manual."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    Preformatted, KeepTogether, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
import os

OUTPUT = os.path.join(os.path.dirname(__file__), "PythonForNinjaTrader.pdf")

def build():
    doc = SimpleDocTemplate(OUTPUT, pagesize=A4,
                            leftMargin=2.5*cm, rightMargin=2.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()

    # Custom styles
    styles.add(ParagraphStyle('MainTitle', parent=styles['Title'],
                              fontSize=28, spaceAfter=6, textColor=HexColor('#1a1a2e')))
    styles.add(ParagraphStyle('Subtitle', parent=styles['Normal'],
                              fontSize=14, alignment=TA_CENTER, textColor=HexColor('#555555'),
                              spaceAfter=30))
    styles.add(ParagraphStyle('TocEntry', parent=styles['Normal'],
                              fontSize=11, spaceAfter=4, leftIndent=20))
    styles.add(ParagraphStyle('CodeBlock', parent=styles['Code'],
                              fontSize=8, leftIndent=15, backColor=HexColor('#f5f5f5'),
                              borderPadding=6, spaceBefore=6, spaceAfter=6))
    styles.add(ParagraphStyle('TableHeader', parent=styles['Normal'],
                              fontSize=9, textColor=colors.white, alignment=TA_CENTER))
    styles.add(ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=9))
    styles.add(ParagraphStyle('Footer', parent=styles['Normal'],
                              fontSize=8, textColor=HexColor('#999999'), alignment=TA_CENTER))

    story = []

    # === TITLE PAGE ===
    logo_path = os.path.join(os.path.dirname(__file__), "quantrosoft_logo.png")
    if os.path.exists(logo_path):
        story.append(Spacer(1, 2*cm))
        story.append(Image(logo_path, width=8*cm, height=8*cm, kind='proportional'))
        story.append(Spacer(1, 2*cm))
    else:
        story.append(Spacer(1, 6*cm))
    story.append(Paragraph("Python for NinjaTrader 8", styles['MainTitle']))
    story.append(Paragraph("User Manual", styles['Subtitle']))
    story.append(Spacer(1, 1.5*cm))
    story.append(Paragraph("Write NinjaTrader strategies in Python", styles['Subtitle']))
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph("Copyright (c) 2026 Quantrosoft", styles['Footer']))
    story.append(Paragraph("MIT License", styles['Footer']))
    story.append(PageBreak())

    # === TABLE OF CONTENTS ===
    story.append(Paragraph("Table of Contents", styles['Heading1']))
    story.append(Spacer(1, 10))
    toc = [
        "1. Architecture",
        "2. Prerequisites",
        "3. Quick Start",
        "4. Writing Your First Strategy",
        "5. PARAMETERS Reference",
        "6. API Reference",
        "7. Crystal Ball Example",
        "8. How It Works Internally",
        "9. Limitations",
        "10. Troubleshooting",
    ]
    for entry in toc:
        story.append(Paragraph(entry, styles['TocEntry']))
    story.append(PageBreak())

    # === 1. ARCHITECTURE ===
    story.append(Paragraph("1. Architecture", styles['Heading1']))
    story.append(Paragraph(
        "Python for NinjaTrader bridges NinjaTrader 8 (C#/.NET) with Python via "
        "<b>pythonnet</b> (Python.Runtime.dll). Each Python strategy gets an auto-generated "
        "C# wrapper that handles the NinjaTrader lifecycle.", styles['Normal']))
    story.append(Spacer(1, 8))
    story.append(Preformatted(
        "NinjaTrader 8 (C#)\n"
        "    |\n"
        "    +-- Generated C# Wrapper (per strategy)\n"
        "            |\n"
        "            +-- pythonnet (Python.Runtime.dll)\n"
        "                    |\n"
        "                    +-- Your Python Strategy (.py)",
        styles['CodeBlock']))
    story.append(Paragraph(
        "The C# wrapper pushes bar data (OHLCV + time) into Python on each bar update, "
        "and reads back orders and print statements. All order execution happens in C#, "
        "ensuring full NinjaTrader compatibility.", styles['Normal']))
    story.append(Spacer(1, 12))

    # === 2. PREREQUISITES ===
    story.append(Paragraph("2. Prerequisites", styles['Heading1']))
    prereqs = [
        ["Component", "Requirement"],
        ["Python", "3.8 - 3.12 (3.11 recommended)"],
        ["NinjaTrader", "NinjaTrader 8 (installed, run at least once)"],
        ["pythonnet", "pip install pythonnet"],
    ]
    t = Table(prereqs, colWidths=[4*cm, 10*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    # === 3. QUICK START ===
    story.append(Paragraph("3. Quick Start", styles['Heading1']))
    story.append(Paragraph("<b>Step 1:</b> Clone the repository", styles['Normal']))
    story.append(Preformatted(
        "git clone https://github.com/Quantrosoft/PythonForNinjaTrader.git\n"
        "cd PythonForNinjaTrader", styles['CodeBlock']))
    story.append(Paragraph("<b>Step 2:</b> Run the installer", styles['Normal']))
    story.append(Preformatted("python install.py", styles['CodeBlock']))
    story.append(Paragraph(
        "The installer copies all files to your NinjaTrader Custom folder, detects your "
        "Python installation, and generates C# wrappers for all example strategies.",
        styles['Normal']))
    story.append(Paragraph("<b>Step 3:</b> Start NinjaTrader", styles['Normal']))
    story.append(Paragraph(
        "NinjaTrader auto-compiles the generated C# wrappers. Open a chart, right-click "
        "&#8594; Strategies, and you will see PyChrystalBall, PySmaCrossover, etc.",
        styles['Normal']))
    story.append(Spacer(1, 12))

    # === 4. WRITING YOUR FIRST STRATEGY ===
    story.append(Paragraph("4. Writing Your First Strategy", styles['Heading1']))
    story.append(Paragraph(
        "Create a new <font face='Courier'>.py</font> file in "
        "<font face='Courier'>Python/strategies/</font>:", styles['Normal']))
    story.append(Preformatted(
        'from nt_api import NtStrategy\n'
        '\n'
        'class MyStrategy(NtStrategy):\n'
        '    PARAMETERS = {\n'
        "        'period': {\n"
        "            'type': 'int', 'default': 14,\n"
        "            'display': 'Period', 'group': 'MyStrategy'\n"
        '        },\n'
        '    }\n'
        '\n'
        '    def on_bar_update(self):\n'
        '        bar = self._bar_data\n'
        "        close = bar.get('close', 0)\n"
        "        current_bar = bar.get('current_bar', 0)\n"
        '\n'
        '        if current_bar < self.period:\n'
        '            return\n'
        '\n'
        '        # Your trading logic here\n'
        '        if should_buy:\n'
        '            self.enter_long(1, "MyEntry")\n'
        '        elif should_sell:\n'
        '            self.exit_long("MyEntry")',
        styles['CodeBlock']))
    story.append(Paragraph("Then generate the C# wrapper:", styles['Normal']))
    story.append(Preformatted(
        "cd Python\n"
        "python generate_strategy.py strategies/my_strategy.py",
        styles['CodeBlock']))
    story.append(Paragraph(
        "This creates <font face='Courier'>PyMyStrategy.cs</font> (the C# wrapper) and "
        "a NinjaTrader template XML. Restart NinjaTrader or recompile in the NinjaScript "
        "Editor (F5) to pick up the new strategy.", styles['Normal']))
    story.append(PageBreak())

    # === 5. PARAMETERS REFERENCE ===
    story.append(Paragraph("5. PARAMETERS Reference", styles['Heading1']))
    story.append(Paragraph(
        "Each strategy defines a <font face='Courier'>PARAMETERS</font> class variable. "
        "Each key is a snake_case parameter name mapped to a spec dict:", styles['Normal']))
    params_table = [
        ["Key", "Description", "Example"],
        ["type", "Data type", "int, float, double, string, bool"],
        ["default", "Default value", "10, 3.5, True, 'NQ'"],
        ["display", "Name shown in NinjaTrader UI", "'Fast Period'"],
        ["group", "Property group in NT properties", "'MyStrategy'"],
    ]
    t = Table(params_table, colWidths=[2.5*cm, 5*cm, 6.5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Parameters are automatically exposed as NinjaTrader strategy properties in the "
        "generated C# wrapper. In Python, access them as <font face='Courier'>self.period</font> "
        "(the snake_case name from the PARAMETERS dict).", styles['Normal']))
    story.append(Spacer(1, 12))

    # === 6. API REFERENCE ===
    story.append(Paragraph("6. API Reference", styles['Heading1']))
    story.append(Paragraph("<b>Order Methods</b>", styles['Heading3']))
    orders = [
        ["Method", "Description"],
        ["self.enter_long(qty, signal)", "Market order to go long"],
        ["self.enter_short(qty, signal)", "Market order to go short"],
        ["self.exit_long(signal)", "Exit long position at market"],
        ["self.exit_short(signal)", "Exit short position at market"],
        ["self.print(message)", "Print to NinjaTrader Output window"],
    ]
    t = Table(orders, colWidths=[6.5*cm, 7.5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Bar Data</b> (self._bar_data dict)", styles['Heading3']))
    bardata = [
        ["Key", "Description"],
        ["current_bar", "Bar index (0-based from oldest)"],
        ["close", "Current bar close price"],
        ["open", "Current bar open price"],
        ["high", "Current bar high price"],
        ["low", "Current bar low price"],
        ["volume", "Current bar volume"],
        ["time", "Bar timestamp (ISO format)"],
        ["instrument", "Instrument name (e.g., 'NQ 03-26')"],
        ["tick_size", "Minimum price increment"],
    ]
    t = Table(bardata, colWidths=[4*cm, 10*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Lifecycle Methods</b> (override in subclass)", styles['Heading3']))
    lifecycle = [
        ["Method", "When Called"],
        ["on_bar_update()", "Each bar close (main logic goes here)"],
        ["on_configure()", "State.Configure"],
        ["on_data_loaded()", "State.DataLoaded"],
        ["on_stop()", "Strategy terminated"],
    ]
    t = Table(lifecycle, colWidths=[5*cm, 9*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(PageBreak())

    # === 7. CRYSTAL BALL EXAMPLE ===
    story.append(Paragraph("7. Crystal Ball Example", styles['Heading1']))
    story.append(Paragraph(
        "The ChrystalBall strategy demonstrates a unique backtest-only capability: reading "
        "future bar data using NinjaTrader's <font face='Courier'>GetValueAt()</font> method.",
        styles['Normal']))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>How it works:</b>", styles['Normal']))
    story.append(Paragraph(
        "1. The C# wrapper scans future Open prices via "
        "<font face='Courier'>Open.GetValueAt(CurrentBar + i)</font><br/>"
        "2. It finds the maximum and minimum Open within the time window<br/>"
        "3. Python receives max/min values and their bar indices<br/>"
        "4. The strategy enters Long or Short based on which direction offers more profit<br/>"
        "5. It exits when the target bar is reached",
        styles['Normal']))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Parameters:</b>", styles['Normal']))
    cb_params = [
        ["Parameter", "Default", "Description"],
        ["Time Window (sec)", "3600", "How far ahead to look (seconds)"],
        ["Position Size", "1", "Number of contracts"],
        ["Min Profit (Ticks)", "4", "Minimum profit to enter trade"],
        ["Exact Exit Time", "False", "Exit at exact extrema bar vs. trail"],
        ["Target % of Extrema", "100", "Percentage of max move to target"],
    ]
    t = Table(cb_params, colWidths=[4.5*cm, 2*cm, 7.5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "<b>Important:</b> Crystal Ball only works in <b>Historical/Backtest</b> mode. "
        "In live trading, future bars do not exist, so all trades will have zero profit.",
        styles['Normal']))
    story.append(Spacer(1, 12))

    # === 8. HOW IT WORKS ===
    story.append(Paragraph("8. How It Works Internally", styles['Heading1']))
    story.append(Paragraph(
        "1. You write a Python class inheriting from <font face='Courier'>NtStrategy</font> "
        "with a <font face='Courier'>PARAMETERS</font> dict<br/>"
        "2. <font face='Courier'>generate_strategy.py</font> parses your .py file via Python's "
        "AST module and generates:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;a) A C# strategy class (Py{ClassName}.cs)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;b) A NinjaTrader template XML (Default.xml)<br/>"
        "3. NinjaTrader compiles the C# wrapper on startup<br/>"
        "4. At runtime:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;a) C# initializes pythonnet and loads Python.Runtime.dll<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;b) Your Python module is imported<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;c) On each bar, C# pushes OHLCV data as a Python dict<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;d) Python's on_bar_update() runs and queues orders<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;e) C# reads queued orders and executes them in NinjaTrader",
        styles['Normal']))
    story.append(PageBreak())

    # === 9. LIMITATIONS ===
    story.append(Paragraph("9. Limitations", styles['Heading1']))
    limitations = [
        "<b>No direct NT indicator access</b> - Python strategies cannot call NinjaTrader's "
        "built-in indicators (SMA, EMA, etc.) directly. Implement indicators in Python or "
        "use the nt_wrapper.py helper functions.",
        "<b>Crystal Ball is backtest-only</b> - The GetValueAt() future-reading only works "
        "in Historical mode. In live trading, no future data is available.",
        "<b>Single timeframe</b> - The bar-data-push mode supports the primary data series "
        "only. Multi-timeframe strategies require additional C# modifications.",
        "<b>Current bar only</b> - self._bar_data provides the current bar's data. "
        "Historical lookback (close[5]) requires maintaining your own buffer in Python.",
        "<b>Hot-reload limitations</b> - After recompiling C# in a running NinjaTrader "
        "instance, you may need to restart NT if you encounter cast errors.",
    ]
    for lim in limitations:
        story.append(Paragraph("&#8226; " + lim, styles['Normal']))
        story.append(Spacer(1, 4))
    story.append(Spacer(1, 12))

    # === 10. TROUBLESHOOTING ===
    story.append(Paragraph("10. Troubleshooting", styles['Heading1']))
    troubles = [
        ("Unable to cast System.Object to StrategyBase",
         "This error occurs during hot-reload (compiling C# while NinjaTrader is running). "
         "<b>Fix:</b> Close NinjaTrader completely, delete "
         "<font face='Courier'>bin/Custom/bin/Debug/NinjaTrader.Custom.dll</font>, "
         "and restart NinjaTrader."),
        ("Python init failed: Win32Exception",
         "The Python DLL could not be loaded. <b>Fix:</b> Check the Python Home and "
         "Python DLL paths in the strategy properties. Ensure Python 3.8-3.12 is installed "
         "and the paths point to the correct version (e.g., C:\\Python311)."),
        ("No trades in Crystal Ball",
         "Crystal Ball requires <b>Historical</b> playback mode, not Market Replay. "
         "In Market Replay mode, bar data comes from NRD files which don't match the "
         "GetValueAt() data. Switch to Historical in the Playback panel."),
        ("Strategy not appearing in NinjaTrader",
         "The C# wrapper was not generated. <b>Fix:</b> Run "
         "<font face='Courier'>python generate_strategy.py --all</font> from the "
         "Python/ folder, then restart NinjaTrader or recompile (F5 in NinjaScript Editor)."),
        ("NinjaScript Output is empty",
         "Ensure the strategy is <b>Enabled</b> (checkbox in Strategies tab). "
         "Also check that Output 1 tab is selected, not Output 2."),
        ("Strategy disabled immediately after enabling",
         "Check NinjaScript Output for error messages. Common causes: Python script has a "
         "syntax error, or a required Python package is not installed."),
    ]
    for title, fix in troubles:
        story.append(KeepTogether([
            Paragraph(f"<b>{title}</b>", styles['Heading3']),
            Paragraph(fix, styles['Normal']),
            Spacer(1, 8),
        ]))

    # Build
    doc.build(story)
    print(f"PDF created: {OUTPUT}")

if __name__ == "__main__":
    build()

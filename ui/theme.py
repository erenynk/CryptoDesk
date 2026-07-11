class Theme:
    BACKGROUND = "#0A0E14"
    CONTENT_BACKGROUND = "#0D1117"
    SIDEBAR_BACKGROUND = "#10161D"

    CARD_BACKGROUND = "#151B23"
    CARD_BACKGROUND_HOVER = "#18202A"
    CARD_BACKGROUND_SECONDARY = "#11171E"

    BORDER = "#28313D"
    BORDER_HOVER = "#354252"
    BORDER_SOFT = "#222C37"

    TEXT_PRIMARY = "#F3F5F7"
    TEXT_SECONDARY = "#9AA4B2"
    TEXT_MUTED = "#667180"

    ACCENT = "#16C784"
    ACCENT_HOVER = "#19D891"
    ACCENT_SOFT = "#192B27"
    ACCENT_BORDER = "#24473D"

    ERROR = "#F05D6C"
    WARNING = "#F3BA2F"

    FONT_FAMILY = "Segoe UI"

    RADIUS_SMALL = 8
    RADIUS_MEDIUM = 12
    RADIUS_LARGE = 16
    RADIUS_XLARGE = 18

    PAGE_MARGIN_HORIZONTAL = 32
    PAGE_MARGIN_VERTICAL = 28
    PAGE_SPACING = 24


def page_style(object_name):
    return f"""
        QWidget#{object_name} {{
            background-color: {Theme.CONTENT_BACKGROUND};
        }}
    """


def label_style():
    return f"""
        QLabel {{
            background: transparent;
            border: none;
            color: {Theme.TEXT_PRIMARY};
            font-family: "{Theme.FONT_FAMILY}";
        }}
    """


def page_title_style():
    return f"""
        QLabel#pageTitle {{
            color: {Theme.TEXT_PRIMARY};
            font-family: "{Theme.FONT_FAMILY}";
            font-size: 27px;
            font-weight: 700;
        }}

        QLabel#pageSubtitle {{
            color: {Theme.TEXT_SECONDARY};
            font-family: "{Theme.FONT_FAMILY}";
            font-size: 13px;
            font-weight: 400;
        }}
    """


def card_style(
    object_name,
    radius=Theme.RADIUS_LARGE,
    hover=False,
):
    style = f"""
        QFrame#{object_name},
        QWidget#{object_name} {{
            background-color: {Theme.CARD_BACKGROUND};
            border: 1px solid {Theme.BORDER};
            border-radius: {radius}px;
        }}
    """

    if hover:
        style += f"""
            QFrame#{object_name}:hover,
            QWidget#{object_name}:hover {{
                background-color: {Theme.CARD_BACKGROUND_HOVER};
                border-color: {Theme.BORDER_HOVER};
            }}
        """

    return style


def primary_button_style(object_name=None):
    selector = (
        f"QPushButton#{object_name}"
        if object_name
        else "QPushButton"
    )

    return f"""
        {selector} {{
            background-color: {Theme.ACCENT};
            color: #07100D;
            border: 1px solid {Theme.ACCENT};
            border-radius: {Theme.RADIUS_SMALL}px;
            padding: 9px 16px;
            font-family: "{Theme.FONT_FAMILY}";
            font-size: 12px;
            font-weight: 700;
        }}

        {selector}:hover {{
            background-color: {Theme.ACCENT_HOVER};
            border-color: {Theme.ACCENT_HOVER};
        }}

        {selector}:pressed {{
            background-color: #13B878;
            border-color: #13B878;
        }}

        {selector}:disabled {{
            background-color: {Theme.CARD_BACKGROUND_SECONDARY};
            color: {Theme.TEXT_MUTED};
            border-color: {Theme.BORDER_SOFT};
        }}
    """


def secondary_button_style(object_name=None):
    selector = (
        f"QPushButton#{object_name}"
        if object_name
        else "QPushButton"
    )

    return f"""
        {selector} {{
            background-color: {Theme.CARD_BACKGROUND_SECONDARY};
            color: {Theme.TEXT_PRIMARY};
            border: 1px solid {Theme.BORDER};
            border-radius: {Theme.RADIUS_SMALL}px;
            padding: 9px 16px;
            font-family: "{Theme.FONT_FAMILY}";
            font-size: 12px;
            font-weight: 600;
        }}

        {selector}:hover {{
            background-color: {Theme.CARD_BACKGROUND_HOVER};
            border-color: {Theme.BORDER_HOVER};
        }}

        {selector}:pressed {{
            background-color: #1B2530;
        }}

        {selector}:disabled {{
            background-color: #10161D;
            color: {Theme.TEXT_MUTED};
            border-color: {Theme.BORDER_SOFT};
        }}
    """


def checkbox_style(object_name=None):
    selector = (
        f"QCheckBox#{object_name}"
        if object_name
        else "QCheckBox"
    )

    return f"""
        {selector} {{
            color: {Theme.TEXT_SECONDARY};
            spacing: 8px;
            font-family: "{Theme.FONT_FAMILY}";
            font-size: 12px;
            font-weight: 500;
        }}

        {selector}::indicator {{
            width: 16px;
            height: 16px;
            background-color: {Theme.CARD_BACKGROUND_SECONDARY};
            border: 1px solid {Theme.BORDER_HOVER};
            border-radius: 5px;
        }}

        {selector}::indicator:hover {{
            border-color: {Theme.ACCENT};
        }}

        {selector}::indicator:checked {{
            background-color: {Theme.ACCENT};
            border-color: {Theme.ACCENT};
        }}

        {selector}:disabled {{
            color: {Theme.TEXT_MUTED};
        }}
    """


def scroll_bar_style():
    return f"""
        QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            margin: 6px 2px 6px 2px;
        }}

        QScrollBar::handle:vertical {{
            background-color: #2B3541;
            min-height: 36px;
            border-radius: 4px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: #3A4654;
        }}

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
            background: transparent;
            border: none;
        }}

        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {{
            background: transparent;
        }}

        QScrollBar:horizontal {{
            background: transparent;
            height: 10px;
            margin: 2px 6px 2px 6px;
        }}

        QScrollBar::handle:horizontal {{
            background-color: #2B3541;
            min-width: 36px;
            border-radius: 4px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: #3A4654;
        }}

        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0;
            background: transparent;
            border: none;
        }}

        QScrollBar::add-page:horizontal,
        QScrollBar::sub-page:horizontal {{
            background: transparent;
        }}
    """


def table_style(object_name="portfolioTable"):
    return f"""
        QTableWidget#{object_name} {{
            background-color: {Theme.CARD_BACKGROUND};
            color: {Theme.TEXT_PRIMARY};
            border: 1px solid {Theme.BORDER};
            border-radius: {Theme.RADIUS_LARGE}px;
            gridline-color: transparent;
            outline: none;
            selection-background-color: transparent;
        }}

        QTableWidget#{object_name}::item {{
            color: {Theme.TEXT_PRIMARY};
            background-color: transparent;
            border: none;
            border-bottom: 1px solid {Theme.BORDER_SOFT};
            padding: 11px 12px;
        }}

        QTableWidget#{object_name}::item:hover {{
            background-color: {Theme.CARD_BACKGROUND_HOVER};
        }}

        QTableWidget#{object_name}::item:selected {{
            color: {Theme.TEXT_PRIMARY};
            background-color: #1B2530;
            border: none;
        }}

        QHeaderView::section:horizontal {{
            background-color: {Theme.CARD_BACKGROUND_SECONDARY};
            color: {Theme.TEXT_SECONDARY};
            border: none;
            border-bottom: 1px solid {Theme.BORDER};
            padding: 11px 12px;
            font-family: "{Theme.FONT_FAMILY}";
            font-size: 11px;
            font-weight: 700;
        }}

        QHeaderView::section:horizontal:hover {{
            color: {Theme.TEXT_PRIMARY};
            background-color: {Theme.CARD_BACKGROUND_HOVER};
        }}

        QHeaderView::section:vertical {{
            background-color: {Theme.CARD_BACKGROUND};
            color: {Theme.TEXT_MUTED};
            border: none;
            border-right: 1px solid {Theme.BORDER_SOFT};
            border-bottom: 1px solid {Theme.BORDER_SOFT};
            padding: 8px;
            font-family: "{Theme.FONT_FAMILY}";
            font-size: 11px;
            font-weight: 600;
        }}

        QTableCornerButton::section {{
            background-color: {Theme.CARD_BACKGROUND_SECONDARY};
            border: none;
            border-bottom: 1px solid {Theme.BORDER};
        }}

        QHeaderView::down-arrow,
        QHeaderView::up-arrow {{
            image: none;
            width: 0;
            height: 0;
        }}

        {scroll_bar_style()}
    """
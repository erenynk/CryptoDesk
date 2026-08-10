from pathlib import Path
import argparse
import shutil


IMPORT_ANCHOR = "from ui.settings import SettingsPage\n"
IMPORT_LINE = "from ui.trade_history import TradeHistoryPage\n"

MENU_ANCHOR = '            ("Portfolio", "portfolio", "#18C98B"),\n'
MENU_LINE = '            ("İşlem Geçmişi", "history", "#55D6B2"),\n'

ICON_ANCHOR = '        elif name == "watchlist":\n'
ICON_BLOCK = (
    '        elif name == "history":\n'
    '            painter.drawEllipse(QRectF(4, 4, 14, 14))\n'
    '            painter.drawLine(QPointF(11, 7), QPointF(11, 11))\n'
    '            painter.drawLine(QPointF(11, 11), QPointF(15, 13))\n'
)

PAGE_CREATE_ANCHOR = (
    '        self.watchlist_page = WatchlistPage(self.data_manager)\n'
)
PAGE_CREATE_LINE = (
    '        self.trade_history_page = TradeHistoryPage(\n'
    '            self.data_manager\n'
    '        )\n'
)

PAGE_ADD_ANCHOR = '        self.pages.addWidget(self.watchlist_page)\n'
PAGE_ADD_LINE = '        self.pages.addWidget(self.trade_history_page)\n'

SHUTDOWN_ANCHOR = (
    '        if portfolio_page is not None:\n'
    '            portfolio_page.shutdown()\n'
)
SHUTDOWN_BLOCK = (
    '        if portfolio_page is not None:\n'
    '            portfolio_page.shutdown()\n'
    '\n'
    '        trade_history_page = getattr(\n'
    '            self,\n'
    '            "trade_history_page",\n'
    '            None,\n'
    '        )\n'
    '        if trade_history_page is not None:\n'
    '            trade_history_page.shutdown()\n'
)


def insert_after_once(text, anchor, addition, label):
    if addition in text:
        return text

    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(
            f"{label}: beklenen anchor sayısı 1, bulunan {count}."
        )

    return text.replace(anchor, anchor + addition, 1)


def insert_before_once(text, anchor, addition, label):
    if addition in text:
        return text

    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(
            f"{label}: beklenen anchor sayısı 1, bulunan {count}."
        )

    return text.replace(anchor, addition + anchor, 1)


def replace_once(text, anchor, replacement, label):
    if replacement in text:
        return text

    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(
            f"{label}: beklenen anchor sayısı 1, bulunan {count}."
        )

    return text.replace(anchor, replacement, 1)


def patch_main_window(text):
    text = insert_after_once(
        text,
        IMPORT_ANCHOR,
        IMPORT_LINE,
        "TradeHistoryPage import",
    )
    text = insert_after_once(
        text,
        MENU_ANCHOR,
        MENU_LINE,
        "İşlem Geçmişi menüsü",
    )
    text = insert_before_once(
        text,
        ICON_ANCHOR,
        ICON_BLOCK,
        "İşlem Geçmişi ikonu",
    )
    text = insert_before_once(
        text,
        PAGE_CREATE_ANCHOR,
        PAGE_CREATE_LINE,
        "TradeHistoryPage oluşturma",
    )
    text = insert_before_once(
        text,
        PAGE_ADD_ANCHOR,
        PAGE_ADD_LINE,
        "TradeHistoryPage stack",
    )
    text = replace_once(
        text,
        SHUTDOWN_ANCHOR,
        SHUTDOWN_BLOCK,
        "TradeHistoryPage shutdown",
    )
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    main_window_path = project_root / "ui" / "main_window.py"
    trade_history_path = project_root / "ui" / "trade_history.py"

    if not main_window_path.is_file():
        raise SystemExit(f"Bulunamadı: {main_window_path}")

    if not trade_history_path.is_file():
        raise SystemExit(f"Bulunamadı: {trade_history_path}")

    original = main_window_path.read_text(encoding="utf-8")
    patched = patch_main_window(original)

    if patched == original:
        print("main_window.py zaten güncel.")
        return

    backup_path = main_window_path.with_suffix(
        ".py.trade-history-ui.bak"
    )
    shutil.copy2(main_window_path, backup_path)
    main_window_path.write_text(patched, encoding="utf-8")

    print(f"Güncellendi: {main_window_path}")
    print(f"Yedek: {backup_path}")


if __name__ == "__main__":
    main()

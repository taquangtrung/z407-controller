"""Z407 Controller GUI - Web-based and native PySide6 interface."""


def launch_native_gui() -> None:
    """Launch the native PySide6 desktop GUI."""
    from z407.gui.app import run_gui

    run_gui()

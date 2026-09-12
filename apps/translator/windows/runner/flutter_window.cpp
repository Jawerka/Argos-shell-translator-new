#include "flutter_window.h"

#include <optional>

#include "flutter/generated_plugin_registrant.h"
#include "single_instance.h"

FlutterWindow::FlutterWindow(const flutter::DartProject& project)
    : project_(project) {}

FlutterWindow::~FlutterWindow() {}

bool FlutterWindow::OnCreate() {
  if (!Win32Window::OnCreate()) {
    return false;
  }

  RECT frame = GetClientArea();

  // The size here must match the window dimensions to avoid unnecessary surface
  // creation / destruction in the startup path.
  flutter_controller_ = std::make_unique<flutter::FlutterViewController>(
      frame.right - frame.left, frame.bottom - frame.top, project_);
  // Ensure that basic setup of the controller was successful.
  if (!flutter_controller_->engine() || !flutter_controller_->view()) {
    return false;
  }
  RegisterPlugins(flutter_controller_->engine());
  SetChildContent(flutter_controller_->view()->GetNativeWindow());

  flutter_controller_->engine()->SetNextFrameCallback([&]() {
    // Visibility is controlled from Dart (DesktopShell show/hide).
    // Do not Show() here — it races with start_minimized / hideToTray.
  });

  // Flutter can complete the first frame before the next-frame callback is
  // registered. Force a pending frame so Dart can apply launch visibility.
  flutter_controller_->ForceRedraw();

  return true;
}

void FlutterWindow::OnDestroy() {
  if (flutter_controller_) {
    flutter_controller_ = nullptr;
  }

  Win32Window::OnDestroy();
}

LRESULT
FlutterWindow::MessageHandler(HWND hwnd, UINT const message,
                              WPARAM const wparam,
                              LPARAM const lparam) noexcept {
  // Give Flutter, including plugins, an opportunity to handle window messages.
  if (flutter_controller_) {
    std::optional<LRESULT> result =
        flutter_controller_->HandleTopLevelWindowProc(hwnd, message, wparam,
                                                      lparam);
    if (result) {
      return *result;
    }
  }

  if (message == argos::ShowWindowMessage()) {
    // Dart hideToTray may have set WS_EX_TOOLWINDOW (skip taskbar). Clear it
    // so a second launch restores a normal taskbar button.
    LONG_PTR ex_style = GetWindowLongPtr(hwnd, GWL_EXSTYLE);
    ex_style &= ~WS_EX_TOOLWINDOW;
    ex_style |= WS_EX_APPWINDOW;
    SetWindowLongPtr(hwnd, GWL_EXSTYLE, ex_style);
    SetWindowPos(hwnd, nullptr, 0, 0, 0, 0,
                 SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED);

    ShowWindow(hwnd, SW_SHOW);
    if (IsIconic(hwnd)) {
      ShowWindow(hwnd, SW_RESTORE);
    }
    SetForegroundWindow(hwnd);
    BringWindowToTop(hwnd);
    return 0;
  }

  switch (message) {
    case WM_FONTCHANGE:
      flutter_controller_->engine()->ReloadSystemFonts();
      break;
  }

  return Win32Window::MessageHandler(hwnd, message, wparam, lparam);
}

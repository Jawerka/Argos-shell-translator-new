#include "single_instance.h"

namespace argos {
namespace {

constexpr wchar_t kMutexName[] = L"Local\\ArgosTranslateSingleInstance";
constexpr wchar_t kWindowClassName[] = L"FLUTTER_RUNNER_WIN32_WINDOW";
constexpr wchar_t kWindowTitle[] = L"Argos Translate";
constexpr wchar_t kShowMessageName[] = L"ArgosTranslate_ShowWindow";

HANDLE g_mutex = nullptr;

struct FindData {
  HWND hwnd = nullptr;
};

BOOL CALLBACK EnumArgosWindows(HWND hwnd, LPARAM lparam) {
  wchar_t class_name[256];
  if (GetClassNameW(hwnd, class_name, 256) == 0) {
    return TRUE;
  }
  if (wcscmp(class_name, kWindowClassName) != 0) {
    return TRUE;
  }
  wchar_t title[256];
  if (GetWindowTextW(hwnd, title, 256) == 0) {
    return TRUE;
  }
  if (wcscmp(title, kWindowTitle) != 0) {
    return TRUE;
  }
  auto* data = reinterpret_cast<FindData*>(lparam);
  data->hwnd = hwnd;
  return FALSE;
}

HWND FindExistingArgosWindow() {
  FindData data;
  EnumWindows(EnumArgosWindows, reinterpret_cast<LPARAM>(&data));
  return data.hwnd;
}

void ActivateExistingWindow(HWND hwnd) {
  if (hwnd == nullptr) {
    return;
  }
  const UINT show_msg = ShowWindowMessage();
  PostMessageW(hwnd, show_msg, 0, 0);
  ShowWindow(hwnd, SW_SHOW);
  if (IsIconic(hwnd)) {
    ShowWindow(hwnd, SW_RESTORE);
  }
  DWORD pid = 0;
  GetWindowThreadProcessId(hwnd, &pid);
  if (pid != 0) {
    AllowSetForegroundWindow(pid);
  }
  SetForegroundWindow(hwnd);
  BringWindowToTop(hwnd);
}

}  // namespace

UINT ShowWindowMessage() {
  static const UINT msg = RegisterWindowMessageW(kShowMessageName);
  return msg;
}

bool TryBecomeSoleInstance() {
  g_mutex = CreateMutexW(nullptr, TRUE, kMutexName);
  if (g_mutex == nullptr) {
    // Fail open: allow start if mutex cannot be created.
    return true;
  }
  if (GetLastError() == ERROR_ALREADY_EXISTS) {
    HWND existing = FindExistingArgosWindow();
    for (int i = 0; existing == nullptr && i < 20; ++i) {
      Sleep(50);
      existing = FindExistingArgosWindow();
    }
    ActivateExistingWindow(existing);
    CloseHandle(g_mutex);
    g_mutex = nullptr;
    return false;
  }
  return true;
}

void ReleaseSoleInstance() {
  if (g_mutex != nullptr) {
    ReleaseMutex(g_mutex);
    CloseHandle(g_mutex);
    g_mutex = nullptr;
  }
}

}  // namespace argos

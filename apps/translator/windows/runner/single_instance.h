#ifndef RUNNER_SINGLE_INSTANCE_H_
#define RUNNER_SINGLE_INSTANCE_H_

#include <windows.h>

namespace argos {

/// Registered message: existing instance should show/restore its main window.
UINT ShowWindowMessage();

/// Returns true if this process is the first Argos Translate instance.
/// On false, the existing window was asked to show and the caller should exit.
bool TryBecomeSoleInstance();

/// Releases the single-instance mutex (optional; OS releases on process exit).
void ReleaseSoleInstance();

}  // namespace argos

#endif  // RUNNER_SINGLE_INSTANCE_H_

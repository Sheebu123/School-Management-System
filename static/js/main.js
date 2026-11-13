// Main Vanilla JavaScript utilities for ALGIONS SMS

document.addEventListener('DOMContentLoaded', () => {
  // 1. Mark All Present in Attendance Sheet
  const markAllPresentBtn = document.getElementById('btn-mark-all-present');
  if (markAllPresentBtn) {
    markAllPresentBtn.addEventListener('click', () => {
      document.querySelectorAll('input[type="radio"][value="PRESENT"]').forEach(radio => {
        radio.checked = true;
      });
    });
  }

  // 2. Mark All Absent shortcut
  const markAllAbsentBtn = document.getElementById('btn-mark-all-absent');
  if (markAllAbsentBtn) {
    markAllAbsentBtn.addEventListener('click', () => {
      document.querySelectorAll('input[type="radio"][value="ABSENT"]').forEach(radio => {
        radio.checked = true;
      });
    });
  }

  // 3. Auto-dismiss alerts after 5 seconds
  const autoAlerts = document.querySelectorAll('.alert-dismissible');
  autoAlerts.forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    }, 6000);
  });
});

(function bindGuardianDelegatedEvents(global) {
  'use strict';

  if (global.__guardianDelegatedEventsBound) return;
  global.__guardianDelegatedEventsBound = true;

  const doc = global.document;
  const originalSetSubject = global.setSubject;

  function isLegacyGuardianBinding(type, listener) {
    if (typeof listener !== 'function') return false;
    const source = Function.prototype.toString.call(listener);
    if (type === 'input') {
      return source.includes("e.target.id === 'level-slider'")
        && source.includes('window.onSliderChange');
    }
    if (type === 'click') {
      return source.includes("e.target.closest('[data-action]')")
        && source.includes("case 'save-settings'");
    }
    return false;
  }

  if (typeof originalSetSubject === 'function') {
    global.setSubject = function setSubjectWithoutListenerRebind(subject) {
      const addEventListener = doc.addEventListener;
      doc.addEventListener = function addGuardianListenerOnce(type, listener, options) {
        if (isLegacyGuardianBinding(type, listener)) return;
        return addEventListener.call(this, type, listener, options);
      };
      try {
        return originalSetSubject(subject);
      } finally {
        doc.addEventListener = addEventListener;
      }
    };
  }

  doc.addEventListener('input', (event) => {
    if (event.target?.id === 'level-slider' && typeof global.onSliderChange === 'function') {
      global.onSliderChange(event.target.value);
    }
  });

  doc.addEventListener('click', (event) => {
    const target = event.target?.closest?.('[data-action]');
    if (!target) return;

    const action = target.dataset.action;
    const handlers = {
      'go-home': () => { global.location.href = '../../../index.html'; },
      'set-subject': () => global.setSubject?.(target.dataset.subject),
      'set-math-preset': () => global.onSelectMathPreset?.(target.dataset.preset),
      'save-settings': () => global.saveSettings?.(),
      'add-weekly-word': () => global.addWeeklyWord?.(),
      'add-custom-reward': () => global.addCustomReward?.(),
      'show-growth': () => global.showGrowthTab?.(),
      'delete-weekly-word': () => global.deleteWeeklyWord?.(Number.parseInt(target.dataset.idx, 10)),
      'export-backup': () => global.exportBackup?.(),
      'import-backup-trigger': () => global.importBackupTrigger?.(),
      'confirm-restore': () => global.confirmRestore?.(),
      'cancel-restore': () => global.cancelRestore?.(),
    };

    const handler = handlers[action];
    if (!handler) return;
    handler();
    event.stopPropagation();
  });

  doc.addEventListener('change', (event) => {
    if (event.target?.id === 'backup-file-input' && typeof global.onBackupFileSelected === 'function') {
      global.onBackupFileSelected(event);
    }
  });
})(window);

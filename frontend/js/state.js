window.CerebroState = (() => {
  const state = {
    route: 'overview',
    selectedJob: 'JOB-00124',
    jobTab: 'summary',
    jobs: {
      'JOB-00124': { id:'JOB-00124', title:'Fix checkout trigger', meta:'Shopee Tracker · Software Engineering', status:'Awaiting approval', tone:'amber' },
      'JOB-00131': { id:'JOB-00131', title:'Produce episode 014', meta:'Faceless YouTube · Production', status:'Executing', tone:'blue' },
      'JOB-00119': { id:'JOB-00119', title:'Refactor browser session manager', meta:'Shopee Tracker · Software Engineering', status:'Completed', tone:'green' }
    }
  };
  return { get: () => state, set(patch){ Object.assign(state, patch); return state; } };
})();

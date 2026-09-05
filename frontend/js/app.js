(() => {
  const $ = (selector, root=document) => root.querySelector(selector);
  const $$ = (selector, root=document) => [...root.querySelectorAll(selector)];
  const state = CerebroState.get();

  const jobTabs = {
    summary: `<div class="job-tab-grid"><section class="panel-card"><span class="eyebrow">Objective</span><h2>Restore reliable checkout triggering</h2><p class="muted">Diagnose the stale Playwright page reference, propose the smallest reliable repair, verify it, and preserve the engineer approval boundary before code modification.</p><div class="detail-list"><div><strong>Current stage</strong><span>Approval gate before implementation</span></div><div><strong>Acceptance</strong><span>Trigger succeeds after reconnect and targeted regression tests pass.</span></div></div></section><section class="panel-card"><span class="eyebrow">Ownership</span><h2>Python backend</h2><div class="detail-list"><div><strong>Authority</strong><span>Job state, planning, execution and approvals.</span></div><div><strong>Frontend role</strong><span>Render backend state and collect engineer decisions.</span></div></div></section></div>`,
    requirements: `<section class="panel-card"><h2>Requirements</h2><div class="detail-list"><div><strong>R1 · Reliability</strong><span>Checkout trigger must survive browser reconnection.</span></div><div><strong>R2 · Scope</strong><span>Avoid unrelated refactors.</span></div><div><strong>R3 · Verification</strong><span>Add a regression test that reproduces the stale-page failure mode.</span></div></div></section>`,
    context: `<section class="panel-card"><h2>Project context</h2><div class="detail-list"><div><strong>Runtime</strong><span>Python · Playwright · persistent Chrome context</span></div><div><strong>Relevant module</strong><span>browser_connector.py</span></div><div><strong>Known constraint</strong><span>Browser sessions may reconnect, invalidating previously stored Page objects.</span></div></div></section>`,
    plan: `<section class="panel-card"><h2>Selected plan</h2><div class="detail-list"><div><strong>1 · Reproduce</strong><span>Confirm stale page after reconnect.</span></div><div><strong>2 · Repair</strong><span>Resolve the current Page through the active browser session instead of caching it.</span></div><div><strong>3 · Verify</strong><span>Run targeted and regression tests.</span></div><div><strong>4 · Report</strong><span>Summarize changes, evidence and residual risk.</span></div></div></section>`,
    tasks: `<section class="panel-card"><h2>Task graph</h2><div class="detail-list"><div><strong>T001 · Reproduce</strong><span class="good">Complete</span></div><div><strong>T002 · Compare strategies</strong><span class="good">Complete</span></div><div><strong>T003 · Engineer approval</strong><span>Waiting</span></div><div><strong>T004 · Implement</strong><span>Blocked by T003</span></div><div><strong>T005 · Test</strong><span>Blocked by T004</span></div></div></section>`,
    agents: `<section class="panel-card"><h2>Agent orchestration</h2><div class="detail-list"><div><strong>Planning Agent</strong><span>Selected session-aware accessor strategy.</span></div><div><strong>Coding Agent</strong><span>Queued; cannot write until approval.</span></div><div><strong>Testing Agent</strong><span>Prepared targeted regression scenario.</span></div></div></section>`,
    tools: `<section class="panel-card"><h2>Tool use</h2><div class="detail-list"><div><strong>Filesystem</strong><span>Read project files · write pending approval</span></div><div><strong>Terminal</strong><span>Targeted tests allowed in project environment</span></div><div><strong>Git</strong><span>Read branch state · push requires separate policy</span></div></div></section>`,
    execution: `<section class="panel-card"><div class="card-header"><div><span class="eyebrow">Live state</span><h2>Execution</h2></div><span class="status amber">Blocked by approval</span></div><div class="event-stream"><div><time>12:41:31</time><span class="event-type tool">TEST</span><span>Failure reproduced after browser reconnect.</span></div><div><time>12:41:42</time><span class="event-type plan">PLAN</span><span>Session-aware accessor selected.</span></div><div><time>12:41:57</time><span class="event-type approval">GATE</span><span>Implementation paused for engineer approval.</span></div></div></section>`,
    changes: `<section class="panel-card"><h2>Proposed changes</h2><pre class="muted mono">browser_connector.py
- cache page during initialization
+ resolve active page at operation time

tests/test_browser_connector.py
+ reconnect regression coverage</pre></section>`,
    tests: `<section class="panel-card"><h2>Verification</h2><div class="detail-list"><div><strong>Reproduction test</strong><span class="good">Failure confirmed before patch</span></div><div><strong>Targeted repair test</strong><span>Prepared</span></div><div><strong>Regression suite</strong><span>Queued after implementation</span></div></div></section>`,
    qa: `<section class="panel-card"><h2>Quality gate</h2><div class="detail-list"><div><strong>Scope check</strong><span>Only browser session access path may change.</span></div><div><strong>Test evidence</strong><span>Must include failing-before / passing-after evidence.</span></div><div><strong>Residual risk</strong><span>Must be reported before job completion.</span></div></div></section>`,
    artifacts: `<section class="panel-card"><h2>Artifacts</h2><div class="detail-list"><div><strong>Diagnosis report</strong><span>Generated</span></div><div><strong>Patch</strong><span>Pending approval</span></div><div><strong>Test report</strong><span>Pending execution</span></div></div></section>`,
    approvals: `<section class="panel-card"><h2>Approval boundary</h2><p class="muted">Cerebro may inspect, reason, plan and prepare evidence. It may not modify the project until the engineer approves this change.</p><button class="button primary" data-action="approve">Approve implementation</button></section>`,
    trace: `<section class="panel-card"><h2>Decision trace</h2><div class="detail-list"><div><strong>Understand</strong><span>Checkout action fails after browser reconnection.</span></div><div><strong>Diagnose</strong><span>Stored Page reference points to an invalid session object.</span></div><div><strong>Alternatives</strong><span>Rebuild connector · refresh cached page · resolve active page lazily.</span></div><div><strong>Selected</strong><span>Resolve active page lazily: smallest scope and directly addresses lifecycle mismatch.</span></div></div></section>`,
    experience: `<section class="panel-card"><h2>Relevant experience</h2><div class="detail-list"><div><strong>EX-0032 · Failed strategy</strong><span>Caching Page across reconnect caused stale-handle errors.</span></div><div><strong>Reuse</strong><span>Prefer reacquiring volatile browser handles from the authoritative active context.</span></div></div></section>`
  };

  function routeFromHash(){ return location.hash.replace(/^#\/?/, '').split('/')[0] || 'overview'; }
  function setRoute(route){
    state.route = route;
    $$('.view').forEach(v => v.classList.toggle('active', v.dataset.view === route));
    $$('.nav-item[data-route]').forEach(a => a.classList.toggle('active', a.dataset.route === route));
    $('#sidebar')?.classList.remove('open');
  }
  function renderRoute(){
    const route = routeFromHash();
    const valid = $('.view[data-view="'+route+'"]') ? route : 'overview';
    setRoute(valid);
  }
  function openJob(id){
    const job = state.jobs[id] || state.jobs['JOB-00124'];
    state.selectedJob = job.id; state.jobTab = 'summary';
    $('#jobDetailId').textContent = job.id; $('#jobDetailTitle').textContent = job.title; $('#jobDetailMeta').textContent = job.meta;
    const status = $('#jobDetailStatus'); status.textContent = job.status; status.className = `status ${job.tone}`;
    $$('#jobSubnav button').forEach(b => b.classList.toggle('active', b.dataset.jobTab === 'summary'));
    renderJobTab();
    history.pushState({}, '', '#/job-detail'); renderRoute();
  }
  function renderJobTab(){ $('#jobTabContent').innerHTML = jobTabs[state.jobTab] || jobTabs.summary; }
  function toast(message){ const el=document.createElement('div'); el.className='toast'; el.textContent=message; $('#toastRegion').append(el); setTimeout(()=>el.remove(),2800); }

  window.addEventListener('hashchange', renderRoute);
  document.addEventListener('click', event => {
    const job = event.target.closest('[data-open-job]'); if(job){ openJob(job.dataset.openJob); return; }
    const route = event.target.closest('[data-route-link]'); if(route){ location.hash = '#/' + route.dataset.routeLink; return; }
    const tab = event.target.closest('[data-job-tab]'); if(tab){ state.jobTab=tab.dataset.jobTab; $$('#jobSubnav button').forEach(b=>b.classList.toggle('active',b===tab)); renderJobTab(); return; }
    const action = event.target.closest('[data-action]')?.dataset.action;
    if(action === 'new-job') $('#newJobModal').showModal();
    if(action === 'approve') toast('Approval recorded in the UI prototype. Python API will own the real state.');
  });
  $('#mobileNavToggle').addEventListener('click', () => $('#sidebar').classList.toggle('open'));
  $('#commandForm').addEventListener('submit', e => { e.preventDefault(); const value=$('#commandInput').value.trim(); if(value){ toast(`Command queued: ${value}`); $('#commandInput').value=''; } });
  $('#newJobForm').addEventListener('submit', e => { if(e.submitter?.dataset.submitJob !== undefined){ e.preventDefault(); const objective=$('#newJobObjective').value.trim(); if(!objective) return; $('#newJobModal').close(); toast('Job draft created locally. Connect POST /api/jobs to persist it.'); $('#newJobObjective').value=''; } });
  document.addEventListener('keydown', e => { if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){ e.preventDefault(); $('#commandInput').focus(); } if(e.key==='Escape') $('#sidebar').classList.remove('open'); });

  renderJobTab(); renderRoute();
})();

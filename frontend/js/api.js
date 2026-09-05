window.CerebroAPI = (() => {
  const config = { baseURL: '/api', wsURL: '/ws/events' };

  async function request(path, options = {}) {
    const response = await fetch(config.baseURL + path, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options
    });
    if (!response.ok) throw new Error(`API ${response.status}`);
    return response.status === 204 ? null : response.json();
  }

  return {
    config,
    request,
    listJobs: () => request('/jobs'),
    getJob: id => request(`/jobs/${encodeURIComponent(id)}`),
    createJob: payload => request('/jobs', { method: 'POST', body: JSON.stringify(payload) }),
    approve: id => request(`/approvals/${encodeURIComponent(id)}/approve`, { method: 'POST' }),
    connectEvents(onEvent) {
      const socket = new WebSocket(config.wsURL);
      socket.addEventListener('message', event => {
        try { onEvent(JSON.parse(event.data)); } catch { /* ignore malformed event */ }
      });
      return socket;
    }
  };
})();

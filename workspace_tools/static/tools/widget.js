(() => {
  const source = document.currentScript;
  const endpoint = source && source.dataset.feedbackUrl;
  if (!endpoint || !/^https?:\/\//.test(endpoint)) return;
  fetch(endpoint, { credentials: 'omit' }).then(response => {
    if (!response.ok) throw new Error('Unregistered feedback site');
    return response.json();
  }).then(config => {
    const host = document.createElement('div');
    const root = host.attachShadow({ mode: 'closed' });
    const style = document.createElement('style');
    style.textContent = ':host{position:fixed;bottom:24px;right:24px;z-index:2147483000;font:14px system-ui;color:#202229}button{border:0;border-radius:10px;background:#202229;color:white;padding:12px 18px;cursor:pointer}form{width:280px;padding:20px;background:white;border:1px solid #ddd;border-radius:16px;box-shadow:0 8px 32px #0002;margin-bottom:12px}label{display:block;margin:12px 0}textarea,input{box-sizing:border-box;width:100%;border:1px solid #bbb;border-radius:6px;padding:8px;font:inherit}textarea{height:100px}.hidden{display:none}p{font-size:12px}';
    const toggle = document.createElement('button');
    toggle.textContent = config.label;
    toggle.setAttribute('aria-expanded', 'false');
    const form = document.createElement('form');
    form.className = 'hidden';
    const title = document.createElement('strong'); title.textContent = config.label;
    const messageLabel = document.createElement('label'); messageLabel.textContent = 'Your feedback';
    const message = document.createElement('textarea'); message.required = true; message.maxLength = 5000; messageLabel.appendChild(message);
    const emailLabel = document.createElement('label'); emailLabel.textContent = 'Email (optional)';
    const email = document.createElement('input'); email.type = 'email'; emailLabel.appendChild(email);
    const send = document.createElement('button'); send.type = 'submit'; send.textContent = 'Send feedback';
    const result = document.createElement('p'); result.setAttribute('role', 'status');
    const close = document.createElement('button'); close.type = 'button'; close.textContent = 'Close'; close.style.marginLeft = '8px';
    const hide = () => { form.className = 'hidden'; toggle.setAttribute('aria-expanded', 'false'); toggle.focus(); };
    close.onclick = hide;
    toggle.onclick = () => { const hidden = form.className === 'hidden'; form.className = hidden ? '' : 'hidden'; toggle.setAttribute('aria-expanded', String(hidden)); if (hidden) message.focus(); };
    form.addEventListener('keydown', event => { if (event.key === 'Escape') hide(); });
    form.onsubmit = async event => {
      event.preventDefault(); send.disabled = true; result.textContent = '';
      try {
        const response = await fetch(endpoint, { method: 'POST', credentials: 'omit', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: message.value, email: email.value, page_url: location.origin + location.pathname }) });
        if (!response.ok) throw new Error('Could not send. Please try again later.');
        result.textContent = 'Thank you. Your feedback was received.'; message.value = ''; email.value = '';
      } catch (error) { result.textContent = error.message; }
      finally { send.disabled = false; }
    };
    form.append(title, messageLabel, emailLabel, send, close, result);
    root.append(style, form, toggle); document.body.appendChild(host);
  }).catch(() => { /* Unregistered or unavailable widgets remain hidden. */ });
})();

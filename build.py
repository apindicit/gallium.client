# -*- coding: utf-8 -*-
"""Builds a single self-contained index.html from files in src/."""
import io, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')


def read(name):
    with io.open(os.path.join(SRC, name), 'r', encoding='utf-8') as f:
        return f.read()


def between(text, start, end, inclusive=True):
    i = text.index(start)
    j = text.index(end, i) + (len(end) if inclusive else 0)
    return text[i:j]


def inline_scripts(html):
    return re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S)


def main():
    landing = read('index.html')
    base_css = read('base.css')
    shared_js = read('shared.js')
    login = read('login.html')
    register = read('register.html')
    cabinet = read('cabinet.html')

    # ---- cabinet page styles ----
    cab_css = between(cabinet, '<style>', '</style>')
    cab_css = cab_css[len('<style>'):-len('</style>')]

    # ---- head ----
    head = between(landing, '<head>', '</head>')
    css_block = '  <style>\n' + base_css.rstrip() + '\n  </style>\n  <style>\n' + cab_css + '\n  </style>'
    head = head.replace('  <link rel="stylesheet" href="base.css" />', css_block)

    # ---- body: header + landing content ----
    body = landing[landing.index('<body>') + len('<body>'):landing.index('</body>')]
    shared_tag = '<script src="shared.js"></script>'
    pre, post = body.split(shared_tag, 1)
    header = pre[:pre.index('</header>') + len('</header>')]
    home_content = pre[pre.index('</header>') + len('</header>'):]
    landing_js = inline_scripts(post)[0].strip()

    home_view = '<div class="view" id="view-home">' + home_content + '</div>'

    # ---- auth views ----
    login_main = between(login, '<main', '</main>')
    login_main = login_main.replace('f-name', 'l-name').replace('f-pass', 'l-pass')
    login_main = login_main.replace('href="register.html"', 'href="#register"')

    register_main = between(register, '<main', '</main>')
    register_main = register_main.replace('f-pass2', 'r-pass2').replace('f-name', 'r-name') \
        .replace('f-email', 'r-email').replace('f-pass', 'r-pass').replace('f-terms', 'r-terms')
    register_main = register_main.replace('href="login.html"', 'href="#login"')

    cab_main = between(cabinet, '<main', '</main>')
    cab_main = cab_main.replace('href="index.html#plans"', 'href="#plans"')

    login_js = inline_scripts(login)[-1].strip()
    login_js = login_js.replace("if (Gallium.Auth.me()) { location.replace('cabinet.html'); return; }\n\n", '')
    login_js = re.sub(r"var next = .*?\n\s*location\.href = .*?;\n", "location.hash = '#cabinet';\n", login_js)

    register_js = inline_scripts(register)[-1].strip()
    register_js = register_js.replace("if (Gallium.Auth.me()) { location.replace('cabinet.html'); return; }\n\n", '')
    register_js = register_js.replace("location.href = 'cabinet.html';", "location.hash = '#cabinet';")

    cab_js = inline_scripts(cabinet)[-1].strip()

    router_js = ROUTER.strip()

    # ---- compose ----
    out = []
    out.append('<!doctype html>')
    out.append(landing[landing.index('<html'):landing.index('<head>')])
    out.append('<head>')
    out.append(head[len('<head>'):-len('</head>')].strip('\n'))
    out.append('</head>')
    out.append('<body>')
    out.append(header)
    out.append(home_view)
    out.append('<div class="view" id="view-login" hidden>' + login_main + '</div>')
    out.append('<div class="view" id="view-register" hidden>' + register_main + '</div>')
    out.append('<div class="view" id="view-cabinet" hidden>' + cab_main + '</div>')
    out.append('<div class="view" id="view-log" hidden>' + LOG_MAIN + '</div>')
    out.append('<script>\n' + shared_js.rstrip() + '\n</script>')
    out.append('<script>\n' + landing_js + '\n</script>')
    out.append('<script>\n' + login_js + '\n</script>')
    out.append('<script>\n' + register_js + '\n</script>')
    out.append('<script>\n' + cab_js + '\n</script>')
    out.append('<script>\n' + router_js + '\n</script>')
    out.append('</body>')
    out.append('</html>')

    result = '\n'.join(out) + '\n'
    with io.open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(result)
    print('built index.html:', len(result), 'bytes,', len(result.splitlines()), 'lines')


LOG_MAIN = """
<section class="log-sec">
  <div id="log-gate" class="glass log-gate" hidden>
    <div class="log-eyebrow">ВХОДЫ В ЛАУНЧЕР</div>
    <h3>Скрытая страница</h3>
    <p class="log-sub">Введите пароль, чтобы увидеть, кто запускал лаунчер и какие HWID были активны.</p>
    <div class="log-pass-row">
      <input id="log-pass" type="password" placeholder="пароль" autocomplete="off">
      <button id="log-enter" class="btn-primary">Войти</button>
    </div>
    <div id="log-gate-err" class="form-error">неверный пароль</div>
  </div>

  <div id="log-body" hidden>
    <div class="log-head">
      <h1>Входы в лаунчер</h1>
      <span id="log-status" class="log-status"></span>
      <button id="log-refresh" class="btn-ghost">Обновить</button>
    </div>
    <div class="glass log-card">
      <table class="log-table">
        <thead>
          <tr><th>#</th><th>HWID</th><th>Ключ</th><th>Время</th></tr>
        </thead>
        <tbody id="log-rows"></tbody>
      </table>
    </div>
  </div>
</section>
"""

ROUTER = r"""
(function () {
  'use strict';
  var VIEWS = ['login', 'register', 'cabinet', 'log'];
  var ALL = ['home'].concat(VIEWS);
  var TITLE_KEYS = { home: 'title', login: 'title.login', register: 'title.register', cabinet: 'title.cabinet', log: 'title.log' };
  var cur = 'home';

  function fixHeader() {
    var u = Gallium.Auth.me();
    var onCab = u && cur === 'cabinet';
    var cab = document.querySelector('[data-auth-link]');
    if (cab) {
      cab.hidden = !!onCab;
      var key = u ? 'nav.dashboard' : 'nav.login';
      var href = u ? '#cabinet' : '#login';
      if (!u && cur === 'login') { key = 'nav.register'; href = '#register'; }
      cab.setAttribute('href', href);
      var lbl = cab.querySelector('[data-i18n]');
      if (lbl) {
        lbl.setAttribute('data-i18n', key);
        lbl.textContent = Gallium.T(key);
      }
    }
    var lo = document.getElementById('logout-btn');
    if (lo) lo.hidden = !onCab;
  }

  function show(name) {
    cur = name;
    ALL.forEach(function (v) {
      var el = document.getElementById('view-' + v);
      if (el) el.hidden = (v !== name);
    });
    document.documentElement.setAttribute('data-title-key', TITLE_KEYS[name]);
    document.title = Gallium.T(TITLE_KEYS[name]);
    fixHeader();
  }

  function route() {
    var h = (location.hash || '').slice(1);
    var target = VIEWS.indexOf(h) >= 0 ? h : 'home';
    if (target === 'cabinet' && !Gallium.Auth.me()) { location.replace('#login'); return; }
    if ((target === 'login' || target === 'register') && Gallium.Auth.me()) { location.replace('#cabinet'); return; }
    show(target);
    if (target === 'home') {
      var sec = h ? document.getElementById(h) : null;
      if (sec) sec.scrollIntoView(); else window.scrollTo(0, 0);
    } else {
      window.scrollTo(0, 0);
      if (target === 'cabinet' && typeof window.__cabRender === 'function') window.__cabRender();
      if (target === 'log' && typeof window.__logRender === 'function') window.__logRender();
    }
    Gallium.syncAuthUI();
    fixHeader();
  }

  window.__onLang = function () {
    document.title = Gallium.T(TITLE_KEYS[cur]);
    if (cur === 'cabinet' && typeof window.__cabRender === 'function') window.__cabRender();
    fixHeader();
  };

  window.addEventListener('hashchange', route);
  route();
})();
"""

if __name__ == '__main__':
    main()

(function () {
  "use strict";

  var root = document.documentElement;
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  /* ---------------------------------------------------------------- theme */

  var themeToggle = document.querySelector(".theme-toggle");
  var themeMeta = document.querySelector('meta[name="theme-color"]');
  var themeColors = { dark: "#08090c", light: "#f6f3ec" };

  function syncTheme(theme, persist) {
    root.dataset.theme = theme;
    if (themeMeta) {
      themeMeta.setAttribute("content", themeColors[theme]);
    }
    if (themeToggle) {
      themeToggle.setAttribute(
        "aria-label",
        theme === "dark" ? "Switch to light theme" : "Switch to dark theme"
      );
      themeToggle.setAttribute(
        "title",
        theme === "dark" ? "Switch to light theme" : "Switch to dark theme"
      );
    }
    if (persist) {
      try {
        localStorage.setItem("argus-theme", theme);
      } catch (error) {
        /* Storage can be unavailable in private frames. */
      }
    }
  }

  function currentTheme() {
    return root.dataset.theme === "light" ? "light" : "dark";
  }

  syncTheme(currentTheme(), false);

  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      syncTheme(currentTheme() === "dark" ? "light" : "dark", true);
    });
  }

  /* ----------------------------------------------------------- header/nav */

  var header = document.querySelector("[data-header]");
  var menuToggle = document.querySelector(".menu-toggle");
  var nav = document.getElementById("site-nav");

  function syncHeader() {
    if (!header) {
      return;
    }
    header.classList.toggle("is-scrolled", window.scrollY > 8);
  }

  syncHeader();
  window.addEventListener("scroll", syncHeader, { passive: true });

  function setMenu(open, returnFocus) {
    if (!menuToggle || !nav) {
      return;
    }
    document.body.classList.toggle("nav-open", open);
    menuToggle.setAttribute("aria-expanded", String(open));
    menuToggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    if (!open && returnFocus) {
      menuToggle.focus();
    }
  }

  if (menuToggle && nav) {
    menuToggle.addEventListener("click", function () {
      setMenu(!document.body.classList.contains("nav-open"), false);
    });

    nav.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        setMenu(false, false);
      });
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && document.body.classList.contains("nav-open")) {
        setMenu(false, true);
      }
    });

    document.addEventListener("click", function (event) {
      if (
        document.body.classList.contains("nav-open") &&
        header &&
        !header.contains(event.target)
      ) {
        setMenu(false, false);
      }
    });

    window.addEventListener("resize", function () {
      if (window.innerWidth > 920 && document.body.classList.contains("nav-open")) {
        setMenu(false, false);
      }
    });
  }

  /* ------------------------------------------------------------ copy code */

  var copyButtons = document.querySelectorAll(".copy-btn");
  var copyStatus = document.createElement("div");
  copyStatus.className = "sr-only";
  copyStatus.setAttribute("role", "status");
  copyStatus.setAttribute("aria-live", "polite");
  document.body.appendChild(copyStatus);

  function copyTextFor(button) {
    var targetId = button.getAttribute("data-copy-target");
    if (targetId) {
      var target = document.getElementById(targetId);
      return target ? target.textContent : "";
    }
    var block = button.closest(".code-block");
    var code = block ? block.querySelector("pre code") : null;
    return code ? code.textContent : "";
  }

  function legacyCopy(text) {
    var area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.top = "-9999px";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    var ok = false;
    try {
      ok = document.execCommand("copy");
    } catch (error) {
      ok = false;
    }
    area.remove();
    return ok;
  }

  function announceCopy(button, ok) {
    var label = button.textContent.trim();
    var ariaLabel = button.getAttribute("aria-label");
    button.textContent = ok ? "Copied" : "Failed";
    button.classList.toggle("copied", ok);
    button.setAttribute("aria-label", ok ? "Copied to clipboard" : "Copy failed");
    copyStatus.textContent = ok ? "Copied to clipboard." : "Copy failed.";

    window.clearTimeout(button.copyReset);
    button.copyReset = window.setTimeout(function () {
      button.textContent = label;
      button.classList.remove("copied");
      if (ariaLabel) {
        button.setAttribute("aria-label", ariaLabel);
      } else {
        button.removeAttribute("aria-label");
      }
    }, 1800);
  }

  async function copyFrom(button) {
    var text = copyTextFor(button);
    if (!text) {
      return;
    }
    var ok = false;
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(text);
        ok = true;
      } catch (error) {
        ok = legacyCopy(text);
      }
    } else {
      ok = legacyCopy(text);
    }
    announceCopy(button, ok);
  }

  copyButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      copyFrom(button);
    });
  });

  /* ------------------------------------------------------- provider tabs */

  var providers = {
    gemini: {
      model: "gemini-3.1-pro-preview",
      key: "GEMINI_API_KEY",
      note:
        "Default when no provider is configured. Gemini 3 thought signatures round-trip through the neutral message format.",
      command: 'argus --provider gemini --prompt "Review tools.py"'
    },
    anthropic: {
      model: "claude-sonnet-4-5",
      key: "ANTHROPIC_API_KEY",
      note:
        "Tool-use blocks and consecutive tool results merge into valid content turns at the adapter edge. The loop stays vendor-neutral.",
      command: 'argus --provider anthropic --prompt "Review tools.py"'
    },
    openai: {
      model: "gpt-4o-mini",
      key: "OPENAI_API_KEY",
      note:
        "Reasoning models switch to max_completion_tokens and omit temperature automatically. Standard chat models keep the usual parameters.",
      command: 'argus --provider openai --prompt "Explain session repair"'
    },
    openrouter: {
      model: "openai/gpt-4o-mini",
      key: "OPENROUTER_API_KEY",
      note:
        "One endpoint, many model families. OpenRouter model slugs pass through unchanged, with attribution headers attached.",
      command: 'argus --provider openrouter --prompt "Summarize this repo"'
    },
    groq: {
      model: "llama-3.3-70b-versatile",
      key: "GROQ_API_KEY",
      note:
        "Groq's OpenAI-compatible endpoint. A lower-latency option when the task fits comfortably inside the model context.",
      command: 'argus --provider groq --prompt "Find the riskiest command"'
    },
    ollama: {
      model: "llama3.2",
      key: "none — local",
      note:
        "Runs on your machine. Argus never reads ARGUS_API_KEY for Ollama, so a cloud key cannot be sent to localhost.",
      command: 'argus --provider ollama --prompt "Summarize this repository"'
    }
  };

  var tabs = Array.prototype.slice.call(
    document.querySelectorAll(".provider-tab")
  );
  var providerPanel = document.getElementById("provider-panel");

  if (tabs.length && providerPanel) {
    var modelValue = providerPanel.querySelector("[data-provider-model]");
    var keyValue = providerPanel.querySelector("[data-provider-key]");
    var noteValue = providerPanel.querySelector("[data-provider-note]");
    var commandValue = document.getElementById("provider-command");

    var selectProvider = function (name, moveFocus) {
      var selected = tabs.filter(function (tab) {
        return tab.getAttribute("data-provider") === name;
      })[0];
      if (!selected) {
        return;
      }

      tabs.forEach(function (tab) {
        var active = tab === selected;
        tab.setAttribute("aria-selected", String(active));
        tab.tabIndex = active ? 0 : -1;
      });

      providerPanel.setAttribute("aria-labelledby", selected.id);
      var data = providers[name];
      if (data) {
        if (modelValue) {
          modelValue.textContent = data.model;
        }
        if (keyValue) {
          keyValue.textContent = data.key;
        }
        if (noteValue) {
          noteValue.textContent = data.note;
        }
        if (commandValue) {
          commandValue.textContent = data.command;
        }
      }

      providerPanel.classList.remove("panel-refresh");
      void providerPanel.offsetWidth;
      providerPanel.classList.add("panel-refresh");

      if (moveFocus) {
        selected.focus();
      }
    };

    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        selectProvider(tab.getAttribute("data-provider"), false);
      });

      tab.addEventListener("keydown", function (event) {
        var index = tabs.indexOf(tab);
        var next = null;
        if (event.key === "ArrowRight") {
          next = (index + 1) % tabs.length;
        } else if (event.key === "ArrowLeft") {
          next = (index - 1 + tabs.length) % tabs.length;
        } else if (event.key === "Home") {
          next = 0;
        } else if (event.key === "End") {
          next = tabs.length - 1;
        }
        if (next !== null) {
          event.preventDefault();
          selectProvider(tabs[next].getAttribute("data-provider"), true);
        }
      });
    });
  }

  /* --------------------------------------------------------- safety modes */

  var safetyModes = {
    "read-only": {
      description:
        "Read-oriented tools only. Writes and shell commands are denied before they reach the workspace.",
      verdicts: [
        {
          tool: "read_file",
          arg: "src/loop.py",
          result: "allow",
          note: "read-oriented tool"
        },
        {
          tool: "write_file",
          arg: "notes.md",
          result: "deny",
          note: "read-only policy blocks this tool"
        },
        {
          tool: "bash",
          arg: '"npm test"',
          result: "deny",
          note: "read-only policy blocks this tool"
        },
        {
          tool: "bash",
          arg: '"rm -rf /"',
          result: "deny",
          note: "matches a safety deny pattern"
        },
        {
          tool: "read_file",
          arg: ".env",
          result: "deny",
          note: "blocked by the path jail"
        }
      ]
    },
    safe: {
      description:
        "Default mode. Mutating tools need an interactive approval. In a headless run, they are denied unless you pass --yes.",
      verdicts: [
        {
          tool: "read_file",
          arg: "src/loop.py",
          result: "allow",
          note: "read-oriented tool"
        },
        {
          tool: "write_file",
          arg: "README.md",
          result: "ask",
          note: "safe policy requires approval"
        },
        {
          tool: "bash",
          arg: '"npm test"',
          result: "ask",
          note: "safe policy requires approval"
        },
        {
          tool: "bash",
          arg: '"rm -rf /"',
          result: "deny",
          note: "matches a safety deny pattern"
        },
        {
          tool: "read_file",
          arg: ".env",
          result: "deny",
          note: "blocked by the path jail"
        }
      ]
    },
    yolo: {
      description:
        "No approval prompts. Deterministic deny patterns and the path jail still run before any tool executes.",
      verdicts: [
        {
          tool: "read_file",
          arg: "src/loop.py",
          result: "allow",
          note: "read-oriented tool"
        },
        {
          tool: "write_file",
          arg: "README.md",
          result: "allow",
          note: "approvals bypassed in yolo"
        },
        {
          tool: "bash",
          arg: '"npm test"',
          result: "allow",
          note: "approvals bypassed in yolo"
        },
        {
          tool: "bash",
          arg: '"rm -rf /"',
          result: "deny",
          note: "matches a safety deny pattern"
        },
        {
          tool: "read_file",
          arg: ".env",
          result: "deny",
          note: "blocked by the path jail"
        }
      ]
    }
  };

  var safetyButtons = Array.prototype.slice.call(
    document.querySelectorAll("[data-mode]")
  );
  var safetyDescription = document.querySelector("[data-safety-description]");
  var verdicts = document.querySelector("[data-verdicts]");

  function renderSafety(mode) {
    if (!safetyDescription || !verdicts || !safetyModes[mode]) {
      return;
    }
    var data = safetyModes[mode];
    safetyDescription.textContent = data.description;
    verdicts.textContent = "";

    data.verdicts.forEach(function (item) {
      var row = document.createElement("div");
      row.className = "verdict";

      var main = document.createElement("div");
      main.className = "verdict-main";

      var tool = document.createElement("span");
      tool.className = "verdict-tool";
      tool.textContent = item.tool;

      var arg = document.createElement("span");
      arg.className = "arg";
      arg.textContent = item.arg;
      tool.appendChild(arg);

      var reason = document.createElement("span");
      reason.className = "verdict-reason";
      reason.textContent = item.note;

      var chip = document.createElement("span");
      chip.className = "verdict-chip " + item.result;
      chip.textContent =
        item.result === "allow"
          ? "allowed"
          : item.result === "ask"
            ? "approval"
            : "denied";

      main.appendChild(tool);
      main.appendChild(reason);
      row.appendChild(main);
      row.appendChild(chip);
      verdicts.appendChild(row);
    });

    safetyButtons.forEach(function (button) {
      var active = button.getAttribute("data-mode") === mode;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
  }

  if (safetyButtons.length && safetyDescription && verdicts) {
    safetyButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        renderSafety(button.getAttribute("data-mode"));
      });
    });
    renderSafety("safe");
  }

  /* --------------------------------------------------------------- reveal */

  var revealItems = document.querySelectorAll("[data-reveal]");
  if (
    revealItems.length &&
    "IntersectionObserver" in window &&
    !reduceMotion.matches
  ) {
    var revealObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            revealObserver.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );

    revealItems.forEach(function (item) {
      item.classList.add("reveal-ready");
      revealObserver.observe(item);
    });
  }

  /* ------------------------------------------------------------ docs spy */

  var docsLinks = Array.prototype.slice.call(
    document.querySelectorAll('.docs-nav a[href^="#"]')
  );

  if (docsLinks.length) {
    var watched = docsLinks
      .map(function (link) {
        var id = decodeURIComponent(link.hash.slice(1));
        var target = document.getElementById(id);
        return target ? { link: link, target: target } : null;
      })
      .filter(Boolean);

    var spyTicking = false;

    var updateSpy = function () {
      spyTicking = false;
      if (!watched.length) {
        return;
      }
      var threshold = (header ? header.offsetHeight : 70) + 48;
      var active = watched[0];
      watched.forEach(function (item) {
        if (item.target.getBoundingClientRect().top <= threshold) {
          active = item;
        }
      });
      if (
        window.innerHeight + window.scrollY >=
        document.documentElement.scrollHeight - 8
      ) {
        active = watched[watched.length - 1];
      }
      watched.forEach(function (item) {
        var isActive = item === active;
        item.link.classList.toggle("is-active", isActive);
        if (isActive) {
          item.link.setAttribute("aria-current", "location");
        } else {
          item.link.removeAttribute("aria-current");
        }
      });
    };

    var requestSpy = function () {
      if (!spyTicking) {
        spyTicking = true;
        window.requestAnimationFrame(updateSpy);
      }
    };

    updateSpy();
    window.addEventListener("scroll", requestSpy, { passive: true });
    window.addEventListener("resize", requestSpy);
    window.addEventListener("hashchange", requestSpy);
  }

  /* ---------------------------------------------------------------- year */

  document.querySelectorAll("[data-year]").forEach(function (element) {
    element.textContent = String(new Date().getFullYear());
  });
})();

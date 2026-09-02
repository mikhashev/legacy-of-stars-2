/**
 * A `.panel` section whose body can be collapsed, remembered per-panel in localStorage
 * (web_version_plan.md W5: "panels collapsible with remembered state"). Most useful once the
 * layout stacks below ~1000px (styles.css), but the toggle works at any width.
 */
import { useState } from "preact/hooks";
import type { ComponentChildren } from "preact";

const KEY_PREFIX = "los.panelOpen.";

function readOpen(id: string, fallback: boolean): boolean {
  try {
    const stored = window.localStorage.getItem(KEY_PREFIX + id);
    return stored === null ? fallback : stored === "1";
  } catch {
    // Private mode, or storage disabled: the panel still collapses, it just forgets on reload.
    return fallback;
  }
}

function writeOpen(id: string, open: boolean): void {
  try {
    window.localStorage.setItem(KEY_PREFIX + id, open ? "1" : "0");
  } catch {
    /* not persisting is not worth telling the player about */
  }
}

export function Collapsible({
  id,
  title,
  extraClass,
  defaultOpen = true,
  children,
}: {
  /** localStorage key suffix; stable across sessions, e.g. "status", "actions". */
  id: string;
  title: string;
  /** Extra class(es) on the outer `<section>`, e.g. for a panel with its own layout rules. */
  extraClass?: string;
  defaultOpen?: boolean;
  children: ComponentChildren;
}) {
  const [open, setOpen] = useState(() => readOpen(id, defaultOpen));
  const toggle = () => {
    setOpen((prev) => {
      const next = !prev;
      writeOpen(id, next);
      return next;
    });
  };
  return (
    <section class={`panel collapsible${extraClass ? ` ${extraClass}` : ""}`} data-open={open}>
      <button class="collapsible-head" onClick={toggle} aria-expanded={open}>
        <h2>{title}</h2>
        <span class="collapsible-chevron" aria-hidden="true">
          {open ? "−" : "+"}
        </span>
      </button>
      {open && <div class="collapsible-body">{children}</div>}
    </section>
  );
}

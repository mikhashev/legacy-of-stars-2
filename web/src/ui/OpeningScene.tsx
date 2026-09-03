import { useState } from "preact/hooks";
import type { Store } from "../store";
import type { ViewState } from "../types";

type ComposerStep = "choices" | "custom" | "draft";

/** The engine truncates a custom reply here (`web_api.WOW_MESSAGE_LIMIT`). */
const MESSAGE_LIMIT = 500;

/**
 * The 1977 WOW! decision (`GameInterface.run_opening_scenario` / `_compose_wow_reply`),
 * shown while `state.wow.decided` is false, then the transmitted/silent result panel.
 */
export function OpeningScene({ view, store }: { view: ViewState; store: Store }) {
  const year = (gen: number) => view.start_year + (gen - 1) * 25;
  const [composerStep, setComposerStep] = useState<ComposerStep>("choices");
  const [customText, setCustomText] = useState("");
  const [draft, setDraft] = useState("");
  const [draftLoading, setDraftLoading] = useState(false);

  if (view.wow.decided && store.state.wowResult) {
    const result = store.state.wowResult;
    const replied = view.wow.replied;
    // The console prints a 100-character excerpt; a player who wrote 500 characters and never
    // saw them again cannot check what Earth actually said, so the whole stored reply is shown
    // (`data.message_full`) in its own scrolling block. Older results without it fall back to
    // the console text alone.
    const sent = typeof result.data?.message_full === "string" ? result.data.message_full : "";
    return (
      <main class="opening-scene">
        <div class="opening-panel">
          <h1>{replied ? "November 1977 - Reply Transmitted" : "November 1977 - Silence Maintained"}</h1>
          <pre class="opening-result-text">{result.message}</pre>
          {replied && sent && (
            <>
              <h2>Message transmitted, in full</h2>
              <pre class="opening-full-message">{sent}</pre>
            </>
          )}
          <button class="primary" onClick={() => store.enterMain()}>
            Begin your mission
          </button>
        </div>
      </main>
    );
  }

  const closeComposer = () => {
    store.closeWowComposer();
    setComposerStep("choices");
    setCustomText("");
    setDraft("");
  };

  const useDraft = async () => {
    setDraftLoading(true);
    try {
      const text = await store.composeDirectorDraft();
      setDraft(text);
      setComposerStep("draft");
    } catch (error) {
      // `perform` already toasts the reason and then rethrows; without this catch the rethrow
      // is an unhandled rejection and the composer silently stays on the choices step.
      store.showToast(`Could not draft a message: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setDraftLoading(false);
    }
  };

  return (
    <main class="opening-scene">
      <div class="opening-panel">
        <h1>LEGACY OF STARS</h1>
        <p class="opening-date">August 15, 1977 - 23:16 EDT</p>
        <p>Big Ear Radio Telescope, Ohio State University</p>
        <p>The automated receiver records a 72-second burst at 1420 MHz.</p>
        <p>
          Signal intensity: 6EQUJ5 (30x background noise)
          <br />
          Direction: Sagittarius (Chi Sagittarii region)
          <br />
          Distance: ~1,800 light-years (disputed estimate)
        </p>
        <p>
          Three days later, reviewing the printout, Dr. Jerry Ehman circles six characters and
          writes: "Wow!"
        </p>
        <p>
          This signal will never repeat.
          <br />
          You must decide Earth's response.
        </p>

        <h2>Critical Decision</h2>
        <p>Do you authorize a reply transmission?</p>

        <div class="opening-options">
          <div class="opening-option">
            <h3>1. YES - Send Reply</h3>
            <ul>
              <li>Message travels 72 generations (1,800 LY)</li>
              <li>
                Response/attack arrives Gen 144 (Year {year(144)})
              </li>
              <li>Immediate: +100 RP, +10% Support</li>
              <li>Warning: Unknown consequences</li>
            </ul>
            <button class="primary" disabled={store.state.busy} onClick={() => store.openWowComposer()}>
              Reply
            </button>
          </div>
          <div class="opening-option">
            <h3>2. NO - Stay Silent</h3>
            <ul>
              <li>Earth remains hidden</li>
              <li>Immediate: -15% attack damage (permanent)</li>
              <li>WOW! mystery unsolved</li>
            </ul>
            <button disabled={store.state.busy} onClick={() => void store.wowSilent()}>
              Stay silent
            </button>
          </div>
        </div>
        <p class="opening-note">
          Note: Most players won't reach Gen 144. This is your legacy decision.
        </p>
      </div>

      {store.state.wowComposerOpen && (
        <div class="modal-backdrop" onClick={closeComposer}>
          <div class="modal composer-modal" onClick={(e) => e.stopPropagation()}>
            <h2>Compose Earth's First Interstellar Message</h2>
            <p>
              You are composing humanity's reply to the WOW! Signal. This message will travel
              1,800 light-years to Chi Sagittarii.
            </p>
            {composerStep === "choices" && (
              <div class="composer-choices">
                <button onClick={() => setComposerStep("custom")}>1. Compose custom message</button>
                <button disabled={draftLoading} onClick={() => void useDraft()}>
                  2. Let the Director draft the message
                </button>
                <button
                  class="primary"
                  onClick={() => {
                    store.closeWowComposer();
                    void store.wowReply("");
                  }}
                >
                  3. Use Standard Format (Default)
                </button>
                <button onClick={closeComposer}>Cancel</button>
              </div>
            )}
            {composerStep === "custom" && (
              <div class="composer-custom">
                <textarea
                  rows={5}
                  maxLength={MESSAGE_LIMIT}
                  placeholder={`Earth's message (max ${MESSAGE_LIMIT} characters)`}
                  value={customText}
                  onInput={(e) => setCustomText((e.target as HTMLTextAreaElement).value)}
                />
                <p class="composer-counter">
                  {customText.length} / {MESSAGE_LIMIT}
                </p>
                <div class="modal-actions">
                  <button onClick={() => setComposerStep("choices")}>Back</button>
                  <button
                    class="primary"
                    onClick={() => {
                      store.closeWowComposer();
                      void store.wowReply(customText);
                    }}
                  >
                    Send
                  </button>
                </div>
              </div>
            )}
            {composerStep === "draft" && (
              <div class="composer-draft">
                <p class="opening-draft-text">Draft: "{draft}"</p>
                <p>Use this message?</p>
                <div class="modal-actions">
                  <button onClick={() => setComposerStep("choices")}>No, go back</button>
                  <button
                    class="primary"
                    onClick={() => {
                      store.closeWowComposer();
                      void store.wowReply(draft);
                    }}
                  >
                    Yes, send it
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}

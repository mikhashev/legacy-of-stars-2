/**
 * Root component: routes between the start screen, the 1977 opening scene and the main
 * game screen, purely off `store.state.phase` (store.ts owns the transitions).
 */
import { Store, useStore } from "./store";
import { LoadingScreen } from "./ui/LoadingScreen";
import { StartScreen } from "./ui/StartScreen";
import { OpeningScene } from "./ui/OpeningScene";
import { MainScreen } from "./ui/MainScreen";
import { HelpModal } from "./ui/HelpModal";
import { Toast } from "./ui/Toast";

export function App({ store }: { store: Store }) {
  const state = useStore(store);

  if (state.phase === "boot") {
    return <LoadingScreen progress={state.bootProgress} error={state.bootError} />;
  }

  if (state.phase === "opening" && state.view) {
    return (
      <>
        <OpeningScene view={state.view} store={store} />
        {state.toast && <Toast text={state.toast} store={store} />}
      </>
    );
  }

  if (state.phase === "main" && state.view) {
    return <MainScreen view={state.view} store={store} />;
  }

  return (
    <>
      <StartScreen store={store} />
      {state.showHelp && <HelpModal store={store} />}
      {state.toast && <Toast text={state.toast} store={store} />}
    </>
  );
}

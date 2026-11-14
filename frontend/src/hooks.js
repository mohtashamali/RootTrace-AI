import { useEffect, useRef, useState } from "react";

/** Loads data, optionally polling until `until(data)` is true. `reload()` refetches and resumes polling. */
export function useLoad(fn, deps, { interval = 0, until } = {}) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const [tick, setTick] = useState(0);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    let alive = true;
    let timer;
    const run = async () => {
      try {
        const data = await fnRef.current();
        if (!alive) return;
        setState({ data, error: null, loading: false });
        if (interval && !(until && until(data))) timer = setTimeout(run, interval);
      } catch (e) {
        if (!alive) return;
        setState((s) => ({ ...s, error: e.message, loading: false }));
        if (interval) timer = setTimeout(run, interval * 2);
      }
    };
    run();
    return () => { alive = false; clearTimeout(timer); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick, interval]);

  return { ...state, reload: () => setTick((t) => t + 1) };
}

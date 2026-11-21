import { useCallback, useEffect, useState } from 'react';
export function useRemoteResource(loader, deps = []) {
  const [state, setState] = useState({ status: 'idle', data: null, error: null });
  const reload = useCallback(async () => {
    setState((s) => ({ ...s, status: 'loading', error: null }));
    try {
      const data = await loader();
      setState({
        status: Array.isArray(data?.items) && data.items.length === 0 ? 'empty' : 'success',
        data,
        error: null,
      });
      return data;
    } catch (error) {
      setState({ status: 'error', data: null, error });
      throw error;
    }
  }, deps);
  useEffect(() => {
    let active = true;
    setState((s) => ({ ...s, status: 'loading' }));
    loader()
      .then((data) => {
        if (active)
          setState({
            status: Array.isArray(data?.items) && data.items.length === 0 ? 'empty' : 'success',
            data,
            error: null,
          });
      })
      .catch((error) => {
        if (active) setState({ status: 'error', data: null, error });
      });
    return () => {
      active = false;
    };
  }, deps);
  return { ...state, reload };
}

"""Document-bound opaque transport shared by governance frames and their shell."""


def runtime_js() -> str:
    """Return the bridge runtime; callers own navigation, snapshots, and completion guards."""
    return r"""
(() => {
  'use strict';
  const OFFER = 'odylith.frame-bridge.offer.v1';

  function surface({readSnapshot}) {
    const actor = Array.from(crypto.getRandomValues(new Uint8Array(16)),
      byte => byte.toString(16).padStart(2, '0')).join('');
    let port = null;
    let disposed = false;
    let pending = false;
    let pendingRoute;
    const embedded = window.parent !== window;

    function publish() {
      if (disposed || !port) return false;
      port.postMessage({kind: 'snapshot', actor, snapshot: readSnapshot()});
      return true;
    }

    function navigate(route) {
      if (disposed || !embedded) return false;
      if (port) port.postMessage({kind: 'navigate', actor, route});
      else {
        pending = true;
        pendingRoute = route;
      }
      return true;
    }

    function offer(event) {
      if (!event.data || event.data.type !== OFFER) return;
      if (!embedded || event.source !== window.parent || event.ports.length !== 1) {
        event.ports.forEach(candidate => candidate.close());
        return;
      }
      if (port) port.close();
      port = event.ports[0];
      publish();
      if (pending) {
        const route = pendingRoute;
        pending = false;
        pendingRoute = undefined;
        navigate(route);
      }
    }

    function dispose() {
      disposed = true;
      window.removeEventListener('message', offer);
      if (port) port.close();
      port = null;
      pending = false;
      pendingRoute = undefined;
    }

    window.addEventListener('message', offer);
    return {publish, navigate, dispose};
  }

  function frame({frame, onSnapshot, onNavigate, onActor}) {
    let active = null;
    let disposed = false;
    let acceptedActor = null;

    function revoke() {
      const retired = active;
      active = null;
      if (retired) retired.close();
    }

    function bind() {
      revoke();
      if (disposed || !frame.contentWindow) return false;
      const channel = new MessageChannel();
      const port = channel.port1;
      let portActor = null;
      active = port;
      port.addEventListener('message', event => {
        if (disposed || active !== port || !event.data) return;
        const data = event.data;
        if (data.kind !== 'snapshot' && data.kind !== 'navigate') return;
        if (typeof data.actor !== 'string' || data.actor.length !== 32 ||
            (portActor !== null && portActor !== data.actor)) {
          revoke();
          return;
        }
        if (portActor === null) {
          portActor = data.actor;
          // Rebinding a port is not a new surface actor; a new Document is.
          if (acceptedActor !== portActor) {
            acceptedActor = portActor;
            if (onActor) onActor(portActor);
          }
        }
        // Actor notification may synchronously revoke, dispose, or replace this binding.
        if (disposed || active !== port) return;
        if (data.kind === 'snapshot') onSnapshot(data.snapshot);
        else onNavigate(data.route);
      });
      port.start();
      try {
        // Opaque file origins need '*'; the capability is offered only to this frame.
        frame.contentWindow.postMessage({type: OFFER}, '*', [channel.port2]);
      } catch (error) {
        revoke();
        channel.port2.close();
        throw error;
      }
      return true;
    }

    function dispose() {
      disposed = true;
      revoke();
    }

    // Navigation intent must revoke before changing the frame; callers bind on load.
    return {bind, revoke, dispose};
  }

  window.OdylithFrameBridge = {surface, frame};
})();
"""

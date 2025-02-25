(() => {
  const isLocalEnv =
    location.hostname === "localhost" || location.hostname === "127.0.0.1";

  function initialize() {
    setIframeSrc();
  }

  function setIframeSrc() {
    const iframe = document.querySelector(".agent-iframe");
    const agentId = "gagdiez.near/docs-gpt/latest";
    const hostname = isLocalEnv
      ? "http://localhost:3000"
      : "https://app.near.ai";

    const url = new URL(hostname);
    url.pathname = `/embed/${agentId}`;
    url.searchParams.append("showThreads", true);
    url.searchParams.append("showOutputAndEnvVars", true);

    if (iframe) {
      iframe.setAttribute("src", url.toString());
    }
  }

  window.addEventListener("load", () => {
    initialize();
  });
})();

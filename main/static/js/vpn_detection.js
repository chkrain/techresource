class ConnectionDetector {
  constructor() {
    this.vpnDetected = false;
    this.speedIsPoor = false;
    this.warningShown = false;
    this.warningDismissed = localStorage.getItem("vpn_warning_dismissed");
  }
  async checkWebRTCLeak() {
    return new Promise((resolve) => {
      const servers = {
        iceServers: [
          { urls: "stun:stun.l.google.com:19302" },
          { urls: "stun:stun1.l.google.com:19302" },
        ],
      };
      const pc = new RTCPeerConnection(servers);
      let localIPs = new Set();
      pc.createDataChannel("");
      pc.createOffer()
        .then((offer) => pc.setLocalDescription(offer))
        .catch(() => {});
      pc.onicecandidate = (event) => {
        if (!event || !event.candidate) {
          resolve({ hasLeak: localIPs.size > 1, ips: Array.from(localIPs) });
          pc.close();
          return;
        }
        const candidate = event.candidate.candidate;
        const ipRegex = /([0-9]{1,3}\.){3}[0-9]{1,3}/;
        const match = candidate.match(ipRegex);
        if (
          match &&
          !match[0].startsWith("192.168.") &&
          !match[0].startsWith("10.") &&
          !match[0].startsWith("172.")
        ) {
          localIPs.add(match[0]);
        }
      };
      setTimeout(() => {
        if (pc) pc.close();
        resolve({ hasLeak: false, ips: [] });
      }, 3000);
    });
  }
  async checkConnectionSpeed() {
    const startTime = performance.now();
    const testUrl = "/static/images/favicon/logo-128.svg?" + Date.now();
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      const response = await fetch(testUrl, {
        method: "GET",
        cache: "no-store",
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (!response.ok) throw new Error("Network error");
      const endTime = performance.now();
      const duration = endTime - startTime;
      return { isSlow: duration > 800, loadTime: duration };
    } catch (error) {
      console.warn("Speed test failed:", error);
      return { isSlow: true, loadTime: null };
    }
  }
  isWebRTCBlocked() {
    return !window.RTCPeerConnection;
  }
  isMobileData() {
    const connection =
      navigator.connection ||
      navigator.mozConnection ||
      navigator.webkitConnection;
    if (connection) {
      return (
        connection.effectiveType === "slow-2g" ||
        connection.effectiveType === "2g"
      );
    }
    return false;
  }
  async detect() {
    const currentDismissed = localStorage.getItem("vpn_warning_dismissed");
    if (currentDismissed === "true") {
      console.log("VPN warning previously dismissed");
      return;
    }
    this.warningDismissed = currentDismissed;
    const isWebRTCBlocked = this.isWebRTCBlocked();
    const webRTCResult = await this.checkWebRTCLeak();
    const speedResult = await this.checkConnectionSpeed();
    const isMobileData = this.isMobileData();
    console.log("Connection check results:", {
      webRTCLeak: webRTCResult.hasLeak,
      localIPs: webRTCResult.ips,
      isSlow: speedResult.isSlow,
      loadTime: speedResult.loadTime,
      isMobileData: isMobileData,
      isWebRTCBlocked: isWebRTCBlocked,
    });
    this.vpnDetected =
      (webRTCResult.hasLeak && webRTCResult.ips.length > 1) || isWebRTCBlocked;
    this.speedIsPoor = speedResult.isSlow || isMobileData;
    if (this.vpnDetected && this.speedIsPoor) {
      this.showWarning("vpn_and_speed");
    } else if (this.vpnDetected) {
      this.showWarning("vpn_only");
    } else if (this.speedIsPoor) {
      this.showWarning("speed_only");
    }
  }
  showWarning(reason) {
    if (this.warningShown) return;
    const currentDismissed = localStorage.getItem("vpn_warning_dismissed");
    if (currentDismissed === "true") {
      console.log("Warning suppressed by localStorage");
      return;
    }
    this.warningShown = true;
    let message = "";
    let icon = "";
    switch (reason) {
      case "vpn_and_speed":
        message = "Включенный VPN может замедлять работу сайта.";
        icon = "fa-shield-alt";
        break;
      case "vpn_only":
        message =
          "С включенным VPN некоторые функции могут работать медленнее.";
        icon = "fa-lock";
        break;
      case "speed_only":
        message =
          "Медленное интернет-соединение. Страницы могут загружаться дольше обычного.";
        icon = "fa-tachometer-alt";
        break;
    }
    this.createToastNotification(message, icon);
  }
  createToastNotification(message, icon) {
    const toast = document.createElement("div");
    toast.className = "vpn-toast-notification";
    toast.innerHTML = `<div class="vpn-toast-content"><i class="fas ${icon}"></i><span>${message}</span><button class="vpn-toast-close"><i class="fas fa-times"></i></button></div><div class="vpn-toast-footer"><button class="vpn-toast-dismiss">Больше не показывать</button></div>`;
    const style = document.createElement("style");
    style.textContent = `.vpn-toast-notification{position:fixed;bottom:20px;right:20px;max-width:380px;background:#2d3748;color:white;border-radius:12px;box-shadow:0 10px 25px rgba(0,0,0,0.2);z-index:10000;animation:slideInRight 0.3s ease;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}@keyframes slideInRight{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}@keyframes slideOutRight{from{transform:translateX(0);opacity:1}to{transform:translateX(100%);opacity:0}}.vpn-toast-content{padding:16px 20px;display:flex;align-items:center;gap:12px;border-bottom:1px solid rgba(255,255,255,0.1)}.vpn-toast-content i{font-size:20px;color:#fbbf24}.vpn-toast-content span{flex:1;font-size:14px;line-height:1.4}.vpn-toast-close{background:none;border:none;color:#9ca3af;cursor:pointer;padding:4px;border-radius:4px}.vpn-toast-close:hover{color:white;background:rgba(255,255,255,0.1)}.vpn-toast-footer{padding:10px 16px;background:rgba(0,0,0,0.2);border-radius:0 0 12px 12px;text-align:right}.vpn-toast-dismiss{background:none;border:none;color:#9ca3af;font-size:12px;cursor:pointer;text-decoration:underline}.vpn-toast-dismiss:hover{color:#fbbf24}`;
    document.head.appendChild(style);
    document.body.appendChild(toast);
    const closeBtn = toast.querySelector(".vpn-toast-close");
    const dismissBtn = toast.querySelector(".vpn-toast-dismiss");
    closeBtn.addEventListener("click", () => {
      toast.style.animation = "slideOutRight 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    });
    dismissBtn.addEventListener("click", () => {
      localStorage.setItem("vpn_warning_dismissed", "true");
      this.warningDismissed = "true";
      toast.style.animation = "slideOutRight 0.3s ease";
      setTimeout(() => toast.remove(), 300);
      console.log("VPN warning dismissed permanently");
    });
    setTimeout(() => {
      if (toast && toast.parentElement) {
        toast.style.animation = "slideOutRight 0.3s ease";
        setTimeout(() => toast.remove(), 300);
      }
    }, 10000);
  }
  static resetDismissed() {
    localStorage.removeItem("vpn_warning_dismissed");
    console.log("VPN warning dismissed flag reset");
  }
}
document.addEventListener("DOMContentLoaded", () => {
  const detector = new ConnectionDetector();
  detector.detect();
});

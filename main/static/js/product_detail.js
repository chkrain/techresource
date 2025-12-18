document.addEventListener("DOMContentLoaded",function(){const e=document.getElementById("mainImage"),t=document.getElementById("mainImageContainer"),n=document.querySelectorAll(".thumbnail"),s=document.getElementById("prevImage"),c=document.getElementById("nextImage"),o=document.getElementById("currentImage"),i=document.getElementById("totalImages"),a=document.getElementById("imageCounter");let r=0;const d=n.length;if(d>1){(a.style.display="block"),(i.textContent=d),(s.disabled=!1),(c.disabled=!1),n.forEach((e,t)=>{e.addEventListener("click",function(){l(t)})}),s.addEventListener("click",function(){(r=(r-1+d)%d),l(r)}),c.addEventListener("click",function(){(r=(r+1)%d),l(r)}),document.addEventListener("keydown",function(e){"ArrowLeft"===e.key?s.click():"ArrowRight"===e.key&&c.click()});let e=0,o=0;if(t){t.addEventListener("touchstart",function(t){e=t.changedTouches[0].screenX}),t.addEventListener("touchend",function(t){(o=t.changedTouches[0].screenX),(function(){const t=50,n=e-o;Math.abs(n)>t&&(n>0?c.click():s.click())})()})}}
function l(t){r=t;const s=n[t],c=s.getAttribute("data-image-src");e&&((e.style.opacity="0"),setTimeout(()=>{(e.src=c),(e.style.opacity="1")},200)),n.forEach((e)=>{e.classList.remove("active"),(e.style.transform="scale(1)")}),s.classList.add("active"),(s.style.transform="scale(1.05)"),(o.textContent=t+1)}
const u=document.querySelector(".add-to-cart-btn");u&&u.addEventListener("click",async function(e){e.preventDefault();const t=this.getAttribute("data-product-id"),n=this.innerHTML;(this.innerHTML='<span class="btn-icon">⏳</span>Добавляем...'),(this.disabled=!0),this.classList.add("loading");try{const e=new FormData(),s=g();s&&e.append("csrfmiddlewaretoken",s);const c=await fetch(`/cart/add/${t}/`,{method:"POST",headers:{"X-Requested-With":"XMLHttpRequest"},body:e,credentials:"same-origin",});if(!c.ok)throw new Error("Network error");const o=await c.json();if(!o.success)
throw new Error(o.error||"Ошибка при добавлении в корзину");h(o.message||"Товар добавлен в корзину!","success"),(this.innerHTML='<span class="btn-icon">✅</span>Добавлено!'),setTimeout(()=>{(this.innerHTML=n),(this.disabled=!1),this.classList.remove("loading")},1500)}catch(e){console.error("Error:",e),h(e.message||"Ошибка при добавлении в корзину","error"),(this.innerHTML=n),(this.disabled=!1),this.classList.remove("loading")}});const m=document.querySelector(".toggle-wishlist-btn");function h(e,t="success"){const n=document.getElementById("toast-container");if(!n)return;const s=document.createElement("div");(s.className=`toast ${t}`),(s.innerHTML=`\n            <span class="toast-icon">${
        "success" === t ? "✅" : "❌"
      }</span>\n            <span class="toast-message">${e}</span>\n        `),n.appendChild(s),setTimeout(()=>s.classList.add("show"),100),setTimeout(()=>{s.classList.remove("show"),setTimeout(()=>{s.parentNode&&s.parentNode.removeChild(s)},300)},3e3)}
function g(){const e=document.querySelector("[name=csrfmiddlewaretoken]");if(e)return e.value;const t=document.querySelector('meta[name="csrf-token"]');if(t)return t.getAttribute("content");const n="csrftoken";let s=null;if(document.cookie&&""!==document.cookie){const e=document.cookie.split(";");for(let t=0;t<e.length;t++){const c=e[t].trim();if(c.substring(0,10)===n+"="){s=decodeURIComponent(c.substring(10));break}}}
return s}
m&&m.addEventListener("click",async function(e){e.preventDefault();const t=this.getAttribute("data-product-id");this.classList.contains("active"),this.querySelector(".btn-icon");(this.disabled=!0),this.classList.add("loading");try{const e=new FormData(),n=g();n&&e.append("csrfmiddlewaretoken",n);const s=await fetch(`/wishlist/toggle/${t}/`,{method:"POST",headers:{"X-Requested-With":"XMLHttpRequest"},body:e,credentials:"same-origin",}),c=await s.json();if(!c.success)throw new Error(c.error);h(c.message,"success"),"added"===c.action?(this.classList.add("active"),(this.innerHTML='<span class="btn-icon">❤️</span>В избранном')):(this.classList.remove("active"),(this.innerHTML='<span class="btn-icon">🤍</span>В избранное'))}catch(e){console.error("Error:",e),h(e.message||"Ошибка при работе с избранным","error")}finally{(this.disabled=!1),this.classList.remove("loading")}})});document.addEventListener('DOMContentLoaded',function(){const quickOrderBtn=document.querySelector('.anonymous-quick-order');if(quickOrderBtn){quickOrderBtn.addEventListener('click',async function(e){e.preventDefault();const productId=this.getAttribute('data-product-id');const productName=this.getAttribute('data-product-name');const originalText=this.innerHTML;this.innerHTML='⏳ Добавляем...';this.disabled=!0;try{const formData=new FormData();formData.append('quantity',1);formData.append('csrfmiddlewaretoken',getCSRFToken());const response=await fetch(`/anonymous-cart/add/${productId}/`,{method:'POST',body:formData,headers:{'X-Requested-With':'XMLHttpRequest'}});const data=await response.json();if(data.success){updateCartBadge(data.cart_count);showToast(`Товар "${productName}" добавлен в заказ`,'success');this.innerHTML='✅ В заказе!';this.style.background='linear-gradient(135deg,#059669 0%,#047857 100%)';setTimeout(()=>{this.innerHTML=originalText;this.disabled=!1;this.style.background='linear-gradient(135deg,#10b981 0%,#059669 100%)'},2000)}else{showToast(data.error||'Ошибка добавления товара','error');this.innerHTML=originalText;this.disabled=!1}}catch(error){console.error('Error:',error);showToast('Ошибка соединения с сервером','error');this.innerHTML=originalText;this.disabled=!1}})}
function updateCartBadge(count){const cartBadge=document.getElementById('anonymousCartCount');if(cartBadge){if(count>0){cartBadge.style.display='inline-block';cartBadge.textContent='';cartBadge.setAttribute('data-count',count);cartBadge.classList.add('pulse');setTimeout(()=>{cartBadge.classList.remove('pulse')},1000)}else{cartBadge.style.display='none'}}}
function getCSRFToken(){const csrfToken=document.querySelector('[name=csrfmiddlewaretoken]');return csrfToken?csrfToken.value:''}
function showToast(message,type='info'){const toastContainer=document.getElementById('toast-container');if(!toastContainer)return;const toast=document.createElement('div');toast.className=`toast toast-${type}`;toast.innerHTML=`
            <div class="toast-content">
                ${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}
                <span>${message}</span>
            </div>
            <button class="toast-close">×</button>
        `;toastContainer.appendChild(toast);setTimeout(()=>{toast.classList.add('show')},10);const closeBtn=toast.querySelector('.toast-close');closeBtn.addEventListener('click',()=>{toast.classList.remove('show');setTimeout(()=>{toast.remove()},300)});setTimeout(()=>{toast.classList.remove('show');setTimeout(()=>{toast.remove()},300)},5000)}
const style=document.createElement('style');style.textContent=`
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.2); }
            100% { transform: scale(1); }
        }
        
        #anonymousCartCount.pulse {
            animation: pulse 0.5s ease-in-out;
        }
        
        /* Стили для уведомлений */
        .toast-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
        }
        
        .toast {
            background: white;
            border-radius: 8px;
            padding: 15px 20px;
            margin-bottom: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            display: flex;
            align-items: center;
            justify-content: space-between;
            min-width: 300px;
            max-width: 400px;
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.3s ease;
        }
        
        .toast.show {
            opacity: 1;
            transform: translateX(0);
        }
        
        .toast-success {
            border-left: 4px solid #10b981;
        }
        
        .toast-error {
            border-left: 4px solid #ef4444;
        }
        
        .toast-info {
            border-left: 4px solid #3b82f6;
        }
        
        .toast-content {
            display: flex;
            align-items: center;
            gap: 10px;
            flex: 1;
        }
        
        .toast-close {
            background: none;
            border: none;
            font-size: 20px;
            cursor: pointer;
            color: #6b7280;
            padding: 0;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
        }
        
        .toast-close:hover {
            background: #f3f4f6;
        }
        
        .login-to-buy-btn {
            background: linear-gradient(135deg, #0052cc 0%, #0047b3 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin-top: 10px;
            width: 100%;
        }
        
        .login-to-buy-btn:hover {
            background: linear-gradient(135deg, #0047b3 0%, #003d99 100%);
            transform: translateY(-2px);
            color: white;
            box-shadow: 0 4px 12px rgba(0, 82, 204, 0.3);
            text-decoration: none;
        }
    `;document.head.appendChild(style)})
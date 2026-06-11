export default defineNuxtConfig({
  compatibilityDate: '2025-05-30',
  modules: ['@nuxtjs/tailwindcss'],
  nitro: {
    routeRules: {
      '/**': {
        headers: {
          'X-Content-Type-Options': 'nosniff',
          'X-Frame-Options': 'SAMEORIGIN',
          'Referrer-Policy': 'strict-origin-when-cross-origin',
          // CSP 作为 XSS 的纵深防线。script-src 不含 unsafe-inline 之外的来源，
          // 阻止注入的 <script src> 外联；连接仅放行自身与游戏数据 API。
          // style/font 放行 Google Fonts。'unsafe-inline' 脚本是 Nuxt 注水与
          // 深色模式探测脚本所必需，暂时保留（已由 DOMPurify 兜底用户内容）。
          'Content-Security-Policy': [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data:",
            "connect-src 'self' https://194823.xyz",
            "frame-ancestors 'self'",
            "base-uri 'self'",
            "form-action 'self'",
          ].join('; '),
        },
      },
    },
  },
  tailwindcss: {
    cssPath: '~/assets/css/main.css',
  },
  app: {
    pageTransition: { name: 'page', mode: 'out-in' },
    head: {
      script: [
        {
          innerHTML: `(function(){try{var m=localStorage.getItem('color-mode');if(m==='dark'||(!m&&window.matchMedia('(prefers-color-scheme:dark)').matches)){document.documentElement.classList.add('dark')}}catch(e){}})()`,
          type: 'text/javascript',
        }
      ],
      title: '凯瑞甘生存2 Wiki',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: '凯瑞甘生存2 (Kerrigan Survival 2) 非官方Wiki - 职业、技能、经济建筑数据' }
      ],
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Noto+Sans+SC:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap' }
      ]
    }
  }
})

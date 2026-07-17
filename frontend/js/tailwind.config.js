// Nearby Marketplace — Tailwind Play CDN config
// Must be loaded BEFORE the Tailwind CDN script so the JIT compiler picks it up.
tailwind = {
    config: {
        darkMode: 'class',
        theme: {
            extend: {
                colors: {
                    'primary':                '#c1502e',
                    'on-primary':             '#ffffff',
                    'secondary':              '#3e5641',
                    'on-secondary':           '#ffffff',
                    'tertiary':               '#1c1b19',
                    'on-tertiary':            '#ffffff',
                    'background':             '#fdf9f2',
                    'on-background':          '#1c1c18',
                    'surface':                '#fdfbf7',
                    'surface-container-low':  '#f7f3ec',
                    'surface-container-high': '#ebe8e1',
                    'surface-container-highest': '#e6e2db',
                    'on-surface-variant':     '#8b716a',
                    'outline':                '#8b716a',
                    'primary-fixed-dim':      '#f0c4b5',
                    'error':                  '#ba1a1a',
                    'error-container':        '#ffdad6',
                    'on-error':               '#ffffff',
                },
                spacing: {
                    'stack-xs':       '4px',
                    'stack-sm':       '8px',
                    'stack-md':       '12px',
                    'stack-lg':       '24px',
                    'stack-xl':       '40px',
                    'margin-mobile':  '16px',
                    'margin-desktop': '48px',
                },
                fontFamily: {
                    'display-lg': ['Georgia', 'serif'],
                    'body-base':  ['Inter', 'sans-serif'],
                    'caps':       ['Inter', 'sans-serif'],
                },
                fontSize: {
                    'display-lg-mobile': ['1.75rem', { lineHeight: '2rem',   fontWeight: '700' }],
                    'display-lg':        ['2.5rem',  { lineHeight: '2.75rem', fontWeight: '700' }],
                },
                gap: {
                    'stack-sm': '8px',
                    'stack-md': '12px',
                    'stack-lg': '24px',
                },
            },
        },
    },
};

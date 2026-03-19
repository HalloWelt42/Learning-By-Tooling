<script>
  // ShieldBadge -- Modulare Abzeichen-Komponente
  // Props: level (0-30), icon (FA-Klasse), size (px), showNum (bool)
  //
  // Tier 1 (1-9):   Flach, dünn, gedämpft
  // Tier 2 (10-18):  Verlauf, solider Rand
  // Tier 3 (19-24):  Doppelrand, Glow
  // Tier 4 (25-30):  Doppelrand, Glow-Animation, Krone

  let { level = 0, icon = 'fa-star', size = 48, showNum = true } = $props()

  const COLORS = [
    {name:"Weiß",    hex:"#8a8a8a"},
    {name:"Gelb",    hex:"#d4a020"},
    {name:"Grün",    hex:"#2d8a48"},
    {name:"Blau",    hex:"#3070cc"},
    {name:"Rot",     hex:"#c03030"},
    {name:"Schwarz", hex:"#505050"},
    {name:"Bronze",  hex:"#b87333"},
    {name:"Silber",  hex:"#b0b0b0"},
    {name:"Gold",    hex:"#daa520"},
    {name:"Platin",  hex:"#a0a8c0"},
  ]

  let color = $derived(level <= 0 ? COLORS[0] : COLORS[Math.min(Math.floor((level - 1) / 3), 9)])
  let tier = $derived(
    level <= 0 ? 0
    : level <= 9 ? 1
    : level <= 18 ? 2
    : level <= 24 ? 3
    : 4
  )
  let h = $derived(Math.round(size * 1.2))
  let iconSize = $derived(Math.round(size * 0.3))
  let numSize = $derived(Math.max(8, Math.round(size * 0.26)))
  let uid = $derived(`sb_${level}_${size}_${Math.random().toString(36).slice(2,6)}`)

  // Shield-Pfade
  let outerPath = $derived(
    `M ${size*0.5} ${h*0.02} L ${size*0.95} ${h*0.15} L ${size*0.95} ${h*0.58} Q ${size*0.95} ${h*0.84} ${size*0.5} ${h*0.98} Q ${size*0.05} ${h*0.84} ${size*0.05} ${h*0.58} L ${size*0.05} ${h*0.15} Z`
  )
  let midPath = $derived(
    `M ${size*0.5} ${h*0.06} L ${size*0.91} ${h*0.17} L ${size*0.91} ${h*0.58} Q ${size*0.91} ${h*0.82} ${size*0.5} ${h*0.94} Q ${size*0.09} ${h*0.82} ${size*0.09} ${h*0.58} L ${size*0.09} ${h*0.17} Z`
  )
  let innerPath = $derived(
    `M ${size*0.5} ${h*0.1} L ${size*0.86} ${h*0.2} L ${size*0.86} ${h*0.58} Q ${size*0.86} ${h*0.79} ${size*0.5} ${h*0.9} Q ${size*0.14} ${h*0.79} ${size*0.14} ${h*0.58} L ${size*0.14} ${h*0.2} Z`
  )
  let innerT1 = $derived(
    `M ${size*0.5} ${h*0.07} L ${size*0.9} ${h*0.18} L ${size*0.9} ${h*0.58} Q ${size*0.9} ${h*0.81} ${size*0.5} ${h*0.93} Q ${size*0.1} ${h*0.81} ${size*0.1} ${h*0.58} L ${size*0.1} ${h*0.18} Z`
  )

  function lighten(hex, pct) {
    const r = parseInt(hex.slice(1,3),16)
    const g = parseInt(hex.slice(3,5),16)
    const b = parseInt(hex.slice(5,7),16)
    const nr = Math.min(255, r + Math.round((255-r)*pct/100))
    const ng = Math.min(255, g + Math.round((255-g)*pct/100))
    const nb = Math.min(255, b + Math.round((255-b)*pct/100))
    return '#' + [nr,ng,nb].map(v => v.toString(16).padStart(2,'0')).join('')
  }

  let light30 = $derived(lighten(color.hex, 30))
  let light40 = $derived(lighten(color.hex, 40))
  let showCrown = $derived(tier === 4 && size >= 36)
  let canShowNum = $derived(showNum && size >= 28 && level > 0)

  // Innenfläche: leichte Einfärbung der Level-Farbe auf bg0
  function mixColor(hex, alpha) {
    const r = parseInt(hex.slice(1,3),16)
    const g = parseInt(hex.slice(3,5),16)
    const b = parseInt(hex.slice(5,7),16)
    // Mix mit dunklem Hintergrund (Näherung)
    const br = 13, bg2 = 13, bb = 15
    const nr = Math.round(br + (r - br) * alpha)
    const ng = Math.round(bg2 + (g - bg2) * alpha)
    const nb = Math.round(bb + (b - bb) * alpha)
    return '#' + [nr,ng,nb].map(v => Math.max(0,Math.min(255,v)).toString(16).padStart(2,'0')).join('')
  }
  let bgInner = $derived(mixColor(color.hex, 0.05))
  let bgMid = $derived(mixColor(color.hex, 0.1))
</script>

<div class="shield" class:tier4={tier === 4} style:--glow="{color.hex}60">
  {#if tier <= 1}
    <!-- TIER 1: Flach, dünn, gedämpft -->
    <svg width={size} height={h} viewBox="0 0 {size} {h}">
      <path d={outerPath} fill={color.hex} opacity="0.5"/>
      <path d={innerT1} fill={bgInner}/>
      {#if canShowNum}
        <text x={size/2} y={h*0.82} text-anchor="middle" font-family="'Orbitron',sans-serif" font-weight="900" letter-spacing="-0.5" font-size={numSize} fill={color.hex} opacity="0.85">{level}</text>
      {/if}
    </svg>
    <i class="fa-solid {icon} icon-center" style="color:{color.hex};font-size:{iconSize}px;opacity:0.7"></i>

  {:else if tier === 2}
    <!-- TIER 2: Verlauf, solider Rand -->
    <svg width={size} height={h} viewBox="0 0 {size} {h}">
      <defs>
        <linearGradient id="g2_{uid}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color={color.hex} stop-opacity="0.8"/>
          <stop offset="100%" stop-color={color.hex} stop-opacity="0.4"/>
        </linearGradient>
      </defs>
      <path d={outerPath} fill="url(#g2_{uid})"/>
      <path d={innerT1} fill={bgInner}/>
      {#if canShowNum}
        <text x={size/2} y={h*0.82} text-anchor="middle" font-family="'Orbitron',sans-serif" font-weight="900" letter-spacing="-0.5" font-size={numSize} fill={color.hex}>{level}</text>
      {/if}
    </svg>
    <i class="fa-solid {icon} icon-center" style="color:{color.hex};font-size:{iconSize}px"></i>

  {:else if tier === 3}
    <!-- TIER 3: Doppelrand, Glow -->
    <svg width={size} height={h} viewBox="0 0 {size} {h}" style="filter:drop-shadow(0 0 4px {color.hex}40)">
      <defs>
        <linearGradient id="g3_{uid}" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color={color.hex}/>
          <stop offset="50%" stop-color={light30}/>
          <stop offset="100%" stop-color={color.hex}/>
        </linearGradient>
      </defs>
      <path d={outerPath} fill="url(#g3_{uid})"/>
      <path d={midPath} fill={bgMid}/>
      <path d={innerPath} fill={bgInner}/>
      {#if canShowNum}
        <text x={size/2} y={h*0.82} text-anchor="middle" font-family="'Orbitron',sans-serif" font-weight="900" letter-spacing="-0.5" font-size={numSize} fill={light30}>{level}</text>
      {/if}
    </svg>
    <i class="fa-solid {icon} icon-center" style="color:{color.hex};font-size:{iconSize}px"></i>

  {:else}
    <!-- TIER 4: Legendär -- Doppelrand, Glow-Puls, Krone, Innenlicht -->
    <svg width={size} height={h} viewBox="0 0 {size} {h}">
      <defs>
        <linearGradient id="g4_{uid}" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color={light40}/>
          <stop offset="50%" stop-color={color.hex}/>
          <stop offset="100%" stop-color={light40}/>
        </linearGradient>
        <radialGradient id="inner4_{uid}" cx="50%" cy="30%">
          <stop offset="0%" stop-color={color.hex} stop-opacity="0.15"/>
          <stop offset="100%" stop-color={bgInner} stop-opacity="1"/>
        </radialGradient>
      </defs>
      {#if showCrown}
        <polygon
          points="{size*0.3},{h*0.12} {size*0.35},{h*0.0} {size*0.43},{h*0.07} {size*0.5},{h*0.0} {size*0.57},{h*0.07} {size*0.65},{h*0.0} {size*0.7},{h*0.12}"
          fill={color.hex} opacity="0.9"
        />
      {/if}
      <path d={outerPath} fill="url(#g4_{uid})"/>
      <path d={midPath} fill={bgMid}/>
      <path d={innerPath} fill="url(#inner4_{uid})"/>
      {#if canShowNum}
        <text x={size/2} y={h*0.82} text-anchor="middle" font-family="'Orbitron',sans-serif" font-weight="900" letter-spacing="-0.5" font-size={numSize} fill={light40}>{level}</text>
      {/if}
    </svg>
    <i class="fa-solid {icon} icon-center" style="color:{light30};font-size:{iconSize}px"></i>
  {/if}
</div>

<style>
  .shield {
    position:relative;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    flex-shrink:0;
  }
  .shield :global(svg) {
    display:block;
  }
  .icon-center {
    position:absolute;
    top:40%;
    left:50%;
    transform:translate(-50%, -50%);
    z-index:1;
    pointer-events:none;
  }
  .tier4 {
    animation:glowPulse 3s ease-in-out infinite;
  }
  @keyframes glowPulse {
    0%, 100% { filter:drop-shadow(0 0 6px var(--glow)); }
    50% { filter:drop-shadow(0 0 14px var(--glow)); }
  }
</style>

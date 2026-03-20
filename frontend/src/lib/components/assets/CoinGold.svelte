<script>
  // CoinGold -- Atomare Goldmünze
  // Props: size (px), animate (idle-Animation an/aus)
  let { size = 24, animate = false } = $props()
</script>

<span
  class="coin-gold"
  class:coin-animate={animate}
  style="width:{size}px;height:{size}px"
></span>

<style>
  .coin-gold {
    display: inline-block;
    border-radius: 50%;
    flex-shrink: 0;
    background: radial-gradient(circle at 35% 35%, #FFD700, #B8860B);
    border: 2px solid #DAA520;
    box-sizing: border-box;
  }
  .coin-animate {
    animation: coin-idle 3s ease-in-out infinite;
  }
  @keyframes coin-idle {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
  }
</style>

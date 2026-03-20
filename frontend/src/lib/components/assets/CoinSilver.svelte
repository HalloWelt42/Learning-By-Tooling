<script>
  // CoinSilver -- Atomare Silbermünze
  // Props: size (px), animate (idle-Animation an/aus)
  let { size = 24, animate = false } = $props()
</script>

<span
  class="coin-silver"
  class:coin-animate={animate}
  style="width:{size}px;height:{size}px"
></span>

<style>
  .coin-silver {
    display: inline-block;
    border-radius: 50%;
    flex-shrink: 0;
    background: radial-gradient(circle at 35% 35%, #E8E8E8, #909090);
    border: 2px solid #A0A0A0;
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

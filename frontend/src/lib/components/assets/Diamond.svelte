<script>
  // Diamond -- Atomarer Diamant (Pentagon-Form)
  // Props: size (px), animate (idle-Animation an/aus)
  let { size = 24, animate = false } = $props()
</script>

<span
  class="diamond"
  class:diamond-animate={animate}
  style="width:{size}px;height:{size}px"
></span>

<style>
  .diamond {
    display: inline-block;
    flex-shrink: 0;
    background: radial-gradient(circle at 30% 30%, #81D4FA, #0288D1);
    border: 2px solid #4FC3F7;
    clip-path: polygon(50% 0%, 100% 38%, 82% 100%, 18% 100%, 0% 38%);
    box-sizing: border-box;
  }
  .diamond-animate {
    animation: diamond-idle 3s ease-in-out infinite;
  }
  @keyframes diamond-idle {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
  }
</style>

<template>
  <div class="stats-section">
    <div class="stat-cards">
      <slot></slot>
    </div>
  </div>
</template>

<style lang="scss">
.stats-section {
  background-color: #8687e7;
  padding: 24px;

  .stat-cards {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 24px;
  }
}
</style>

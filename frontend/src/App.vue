<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="brand">
        <span class="brand-dot"></span>
        <div>
          <p class="brand-title">Doraemon</p>
          <p class="brand-sub">Quant & Task Studio</p>
        </div>
      </div>
      <nav class="nav">
        <router-link to="/" class="nav-link">Tasks</router-link>
        <router-link to="/quant" class="nav-link">Quant</router-link>
      </nav>
    </header>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

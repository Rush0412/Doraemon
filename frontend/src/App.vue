<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="brand">
        <span class="brand-dot"></span>
        <div>
          <h1 class="brand-title">Doraemon Quant Workspace</h1>
          <p class="brand-sub">Enterprise Trading Console</p>
        </div>
      </div>
      <div class="nav">
        <span class="nav-link router-link-active">量化工作台</span>
        <span class="nav-link">设计系统 2.0</span>
      </div>
    </header>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

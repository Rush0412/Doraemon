<template>
  <main class="container">
    <section class="card">
      <header class="header">
        <div>
          <p class="muted" style="margin: 0;">Doraemon platform</p>
          <h1 style="margin: 0;">Doraemon Console</h1>
        </div>
        <nav class="nav">
          <router-link to="/" class="btn-secondary">Tasks</router-link>
          <router-link to="/quant" class="btn-secondary">Quant</router-link>
        </nav>
      </header>
      <router-view />
    </section>
  </main>
</template>

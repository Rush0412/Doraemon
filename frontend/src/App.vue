<template>
  <main class="container">
    <section class="card">
      <header style="display: flex; justify-content: space-between; align-items: center;">
        <div>
          <p style="margin: 0; color: #6b7280;">Doraemon platform</p>
          <h1 style="margin: 0;">Task Console</h1>
        </div>
        <router-link to="/" class="btn-secondary">Home</router-link>
      </header>
      <router-view />
    </section>
  </main>
</template>

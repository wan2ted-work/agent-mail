import { defineStore } from 'pinia';
import { ref, reactive, computed } from 'vue';
import { instanceApi, emailApi } from '../services/api';

export const EMPTY_FILTERS = Object.freeze({
  from_email: '',
  nickname: '',
  subject: '',
  extracted_key: '',
});

export const useAppStore = defineStore('app', () => {
  // ── State ──────────────────────────────────────────────────────────────────
  const secret = ref(localStorage.getItem('secret') || '');
  const instance = ref(null);
  const emails = ref([]);
  const currentEmail = ref(null);

  // Per-operation loading flags so unrelated UI doesn't share one spinner.
  const loading = reactive({
    instance: false,
    emails: false,
    detail: false,
    mutation: false,
  });
  const error = ref(null);

  const emailsPagination = reactive({ total: 0, skip: 0, limit: 20 });
  const filters = reactive({ ...EMPTY_FILTERS });

  // ── Computed ───────────────────────────────────────────────────────────────
  const isAuthenticated = computed(() => !!secret.value && !!instance.value);
  const hasEmails = computed(() => emails.value.length > 0);
  const instanceKeys = computed(() => instance.value?.keys || []);
  const instanceDomains = computed(() => instance.value?.domains || []);
  const canPrevPage = computed(() => emailsPagination.skip > 0);
  const canNextPage = computed(
    () => emailsPagination.skip + emailsPagination.limit < emailsPagination.total
  );
  const rangeStart = computed(() => (emailsPagination.total ? emailsPagination.skip + 1 : 0));
  const rangeEnd = computed(() =>
    Math.min(emailsPagination.skip + emailsPagination.limit, emailsPagination.total)
  );

  // ── Helpers ──────────────────────────────────────────────────────────────--
  /**
   * Run an authenticated request with uniform loading/error handling.
   * @param key one of the `loading` flags
   * @param fn  receives the current secret, returns a promise
   * @param fallback error message if the server didn't supply one
   */
  async function withRequest(key, fn, fallback) {
    if (!secret.value) return;
    loading[key] = true;
    error.value = null;
    try {
      return await fn(secret.value);
    } catch (err) {
      error.value = err.message || fallback;
      console.error(fallback, err);
      throw err;
    } finally {
      loading[key] = false;
    }
  }

  // ── Auth ─────────────────────────────────────────────────────────────────--
  async function setSecret(newSecret) {
    secret.value = newSecret;
    localStorage.setItem('secret', newSecret);
    await loadInstance();
  }

  function clearSecret() {
    secret.value = '';
    instance.value = null;
    emails.value = [];
    currentEmail.value = null;
    localStorage.removeItem('secret');
  }

  // ── Instance ─────────────────────────────────────────────────────────────--
  async function loadInstance() {
    if (!secret.value) return;
    try {
      await withRequest('instance', async (s) => {
        instance.value = (await instanceApi.get(s)).data;
      }, 'Failed to load instance');
    } catch {
      // An invalid/unreachable secret means we can't authenticate — log out.
      clearSecret();
    }
  }

  function updateInstance(data) {
    return withRequest('mutation', async (s) => {
      instance.value = (await instanceApi.update(s, data)).data;
    }, 'Failed to update instance');
  }

  // ── Emails ───────────────────────────────────────────────────────────────--
  function loadEmails(resetPagination = false) {
    if (resetPagination) emailsPagination.skip = 0;
    return withRequest('emails', async (s) => {
      const params = {
        skip: emailsPagination.skip,
        limit: emailsPagination.limit,
        ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== '')),
      };
      const { data } = await emailApi.getList(s, params);
      emails.value = data.items;
      emailsPagination.total = data.total;
    }, 'Failed to load emails');
  }

  function loadEmailDetail(emailId) {
    return withRequest('detail', async (s) => {
      currentEmail.value = (await emailApi.getDetail(s, emailId)).data;
    }, 'Failed to load email');
  }

  function clearCurrentEmail() {
    currentEmail.value = null;
  }

  function nextPage() {
    if (!canNextPage.value) return;
    emailsPagination.skip += emailsPagination.limit;
    return loadEmails();
  }

  function prevPage() {
    if (!canPrevPage.value) return;
    emailsPagination.skip = Math.max(0, emailsPagination.skip - emailsPagination.limit);
    return loadEmails();
  }

  // ── Filters ──────────────────────────────────────────────────────────────--
  function setFilters(newFilters) {
    Object.assign(filters, newFilters);
  }

  function clearFilters() {
    Object.assign(filters, EMPTY_FILTERS);
  }

  // ── Keys ─────────────────────────────────────────────────────────────────--
  function addKey(key) {
    return withRequest('mutation', async (s) => {
      await instanceApi.addKey(s, key);
      await loadInstance();
    }, 'Failed to add key');
  }

  function removeKey(key) {
    return withRequest('mutation', async (s) => {
      await instanceApi.removeKey(s, key);
      await loadInstance();
    }, 'Failed to remove key');
  }

  // ── Custom domains ───────────────────────────────────────────────────────--
  function addDomain(domain) {
    return withRequest('mutation', async (s) => {
      const { data } = await instanceApi.addDomain(s, domain);
      await loadInstance();
      return data; // includes dns_record (MX) to display
    }, 'Failed to add domain');
  }

  function verifyDomain(domain) {
    return withRequest('mutation', async (s) => {
      const { data } = await instanceApi.verifyDomain(s, domain);
      await loadInstance();
      return data; // is_verified true/false (+ message when pending)
    }, 'Failed to verify domain');
  }

  function removeDomain(domain) {
    return withRequest('mutation', async (s) => {
      await instanceApi.removeDomain(s, domain);
      await loadInstance();
    }, 'Failed to remove domain');
  }

  return {
    // State
    secret, instance, emails, currentEmail, loading, error, emailsPagination, filters,
    // Computed
    isAuthenticated, hasEmails, instanceKeys, instanceDomains,
    canPrevPage, canNextPage, rangeStart, rangeEnd,
    // Actions
    setSecret, clearSecret, loadInstance, updateInstance,
    loadEmails, loadEmailDetail, clearCurrentEmail, nextPage, prevPage,
    setFilters, clearFilters, addKey, removeKey, addDomain, verifyDomain, removeDomain,
  };
});

import { createClient } from "@supabase/supabase-js";

// Lightweight Supabase browser client. Requires envs at runtime:
// - NEXT_PUBLIC_SUPABASE_URL
// - NEXT_PUBLIC_SUPABASE_ANON_KEY
export const supabase = (() => {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";
  if (!url || !anon) {
    return undefined as unknown as ReturnType<typeof createClient> | undefined;
  }
  return createClient(url, anon);
})();



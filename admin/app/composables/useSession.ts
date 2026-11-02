import type { User } from "@/client";

export const useSession = () =>
    useState<User | undefined>("session.user", () => undefined);

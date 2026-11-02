import type { User } from "@miraepass/api-client";

export const useSession = () =>
    useState<User | undefined>("session.user", () => undefined);

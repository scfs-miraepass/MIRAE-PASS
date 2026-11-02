import type { StampType } from "@miraepass/api-client";

export const useStampType = () =>
    useState<StampType | undefined>("service.stamp-type", () => undefined);

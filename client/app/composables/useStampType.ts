import type { StampType } from "@/client";

export const useStampType = () =>
    useState<StampType | undefined>("service.stamp-type", () => undefined);

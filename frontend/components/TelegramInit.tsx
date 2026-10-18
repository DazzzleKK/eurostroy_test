"use client";

import { useEffect } from "react";

type TelegramWebApp = {
  ready?: () => void;
  expand?: () => void;
};

type TelegramGlobal = {
  WebApp?: TelegramWebApp;
};

export function TelegramInit() {
  useEffect(() => {
    const telegram = (window as unknown as { Telegram?: TelegramGlobal }).Telegram;
    telegram?.WebApp?.ready?.();
    telegram?.WebApp?.expand?.();
  }, []);

  return null;
}

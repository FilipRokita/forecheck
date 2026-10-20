import type { Metadata, Viewport } from "next";
import "@fontsource-variable/inter";
import "@fontsource-variable/jetbrains-mono";
import "./globals.css";

export const metadata: Metadata = {
  title: "Forecheck",
  description: "How far can you trust a weather forecast? Open-Meteo models scored against IMGW stations.",
};

export const viewport: Viewport = { themeColor: "#0b0c0e" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

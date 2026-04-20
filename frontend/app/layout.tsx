import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FPL Mini-League Rank Simulator",
  description:
    "Monte Carlo simulation + AI transfer advisor + community feedback loop for Fantasy Premier League mini-leagues.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">{children}</body>
    </html>
  );
}

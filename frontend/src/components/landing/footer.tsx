import Link from "next/link";

const footerLinks = ["Product", "Docs", "Privacy", "Terms"];

export function Footer() {
  return (
    <footer className="py-10">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 sm:px-6 md:flex-row md:items-center md:justify-between lg:px-8">
        <div>
          <Link href="/" className="text-sm font-semibold text-white">
            CareerOS
          </Link>
          <p className="mt-2 text-sm text-zinc-500">AI-native workspace for modern career growth.</p>
        </div>
        <nav aria-label="Footer navigation" className="flex flex-wrap gap-5">
          {footerLinks.map((link) => (
            <Link key={link} href="#" className="text-sm text-zinc-500 transition-colors hover:text-white">
              {link}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
  );
}

const steps = ["Search", "Discover", "Research", "Personalize", "Apply"];

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="border-b border-white/10 py-20 sm:py-24">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <p className="text-sm font-medium text-zinc-500">How It Works</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-normal text-white sm:text-4xl">
            A simple flow from search to application.
          </h2>
        </div>

        <ol className="mt-12 grid gap-3 md:grid-cols-5">
          {steps.map((step, index) => (
            <li key={step} className="relative rounded-lg border border-white/10 bg-white/[0.025] p-5">
              <span className="text-xs font-medium text-zinc-500">0{index + 1}</span>
              <p className="mt-5 text-lg font-semibold text-white">{step}</p>
              {index < steps.length - 1 ? (
                <span
                  className="absolute -right-2 top-1/2 hidden h-px w-4 bg-white/20 md:block"
                  aria-hidden="true"
                />
              ) : null}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

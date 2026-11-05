import { Logo } from "@/components/Logo";

/** A grey block that shimmers. Its size is the size of the thing it stands for, so nothing moves when the real page arrives. */
function Block({ className }: { className: string }) {
  return <div className={`skeleton rounded-[14px] border border-border ${className}`} />;
}

/**
 * What the page looks like before its first answer: the same header, controls and cards, as grey blocks of the same size.
 * It follows the layout of `Dashboard`, so keep the two in step.
 */
export function PageSkeleton() {
  return (
    <>
      <header className="sticky top-0 z-20 border-b border-border bg-bg/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1280px] flex-wrap items-center justify-between gap-4 px-4 py-3 sm:px-10 sm:py-2.5">
          <h1>
            <Logo />
          </h1>
          {/* The height of the export button, so the header does not grow when the real one arrives. */}
          <div aria-hidden="true" className="h-11 sm:h-9" />
        </div>
      </header>

      <div aria-hidden="true" className="mx-auto flex max-w-[1280px] flex-col gap-3 px-4 py-4 sm:flex-row sm:flex-wrap sm:items-end sm:gap-x-6 sm:gap-y-3 sm:px-10 sm:py-5">
        <div className="flex flex-col gap-1.5">
          <span className="h-4 max-sm:hidden" />
          <Block className="h-12 w-full rounded-xl sm:h-[46px] sm:w-64" />
        </div>
        <div className="flex flex-col gap-1.5">
          <span className="h-4 max-sm:hidden" />
          <Block className="h-[54px] w-full rounded-xl sm:h-[46px] sm:w-[400px]" />
        </div>
        <div className="flex flex-col gap-1.5">
          <span className="h-4 max-sm:hidden" />
          <Block className="h-[54px] w-full rounded-xl sm:h-[46px] sm:w-[285px]" />
        </div>
      </div>

      <main aria-busy="true" className="mx-auto flex max-w-[1280px] flex-col gap-3 px-4 pb-10 pt-3 sm:gap-4 sm:px-10">
        <p role="status" className="sr-only">
          Loading the app
        </p>
        <div aria-hidden="true" className="flex flex-col gap-3 sm:gap-4">
          <div className="flex flex-col gap-2 pb-1">
            <Block className="h-7 w-full max-w-xl rounded-md max-sm:h-12" />
            <Block className="h-7 w-2/3 max-w-sm rounded-md" />
          </div>
          <div className="flex h-[26px] items-center">
            <Block className="h-4 w-44 rounded" />
          </div>
          <div className="flex flex-wrap gap-3 sm:gap-4">
            <Block className="h-48 flex-[2_1_100%] sm:flex-[2_1_26rem]" />
            <Block className="h-48 flex-[1_1_100%] sm:flex-[1_1_16rem]" />
            <Block className="h-48 flex-[1_1_100%] sm:flex-[1_1_16rem]" />
          </div>
          <div className="flex flex-wrap gap-3 sm:gap-4">
            <Block className="h-[344px] flex-[3_1_100%] lg:flex-[3_1_34rem]" />
            <Block className="h-[344px] flex-[2_1_100%] lg:flex-[2_1_22rem]" />
          </div>
          <Block className="h-[480px] sm:h-[720px]" />
        </div>
      </main>
    </>
  );
}

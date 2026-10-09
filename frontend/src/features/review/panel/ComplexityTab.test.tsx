import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MOCK_REVIEW } from "@/mocks/review";
import { ComplexityTab } from "./ComplexityTab";
import { GrowthScale } from "./GrowthScale";

const { complexity, algorithms } = MOCK_REVIEW;

function setup(props: Partial<Parameters<typeof ComplexityTab>[0]> = {}) {
  const onLocateLines = vi.fn();
  render(
    <ComplexityTab
      complexity={complexity}
      algorithms={algorithms}
      onLocateLines={onLocateLines}
      {...props}
    />,
  );
  return { onLocateLines };
}

describe("ComplexityTab", () => {
  it("shows the headline time and space in Big-O notation", () => {
    setup();
    expect(screen.getByText("Time (worst case)").nextElementSibling).toHaveTextContent("O(n²)");
    // The first "Extra space" label is the headline tile; the rest belong to each function.
    expect(screen.getAllByText("Extra space")[0]!.nextElementSibling).toHaveTextContent("O(1)");
  });

  it("explains how the figures were worked out", () => {
    setup();
    expect(screen.getByText("How this was worked out")).toBeInTheDocument();
    expect(screen.getByText(/outer loop runs up to n times/)).toBeInTheDocument();
  });

  it("breaks complexity down by function, with best, average and worst cases", () => {
    setup();
    const card = screen.getByRole("heading", { name: "hasDuplicates" }).closest("li")!;
    expect(within(card).getByText("Best case").nextElementSibling).toHaveTextContent("O(1)");
    expect(within(card).getByText("Average case").nextElementSibling).toHaveTextContent("O(n²)");
    expect(within(card).getByText("Worst case").nextElementSibling).toHaveTextContent("O(n²)");
  });

  it("names the algorithms it recognised, with alternatives", () => {
    setup();
    expect(screen.getByRole("heading", { name: "Bubble sort" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Brute-force pairwise duplicate check" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Hash set")).toBeInTheDocument();
    expect(screen.getByText(/Built-in sort \(TimSort/)).toBeInTheDocument();
  });

  it("shows how the code reveals the algorithm and whether it is a good fit", () => {
    setup();
    expect(screen.getAllByText("How the code shows it").length).toBe(2);
    expect(screen.getAllByText("Is it a good fit here?").length).toBe(2);
  });

  it("jumps to the code for a function or algorithm", async () => {
    const { onLocateLines } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Lines 16–23" }));
    expect(onLocateLines).toHaveBeenLastCalledWith(16, 23);
    await userEvent.click(screen.getByRole("button", { name: "Lines 4–12" }));
    expect(onLocateLines).toHaveBeenLastCalledWith(4, 12);
  });

  it("says plainly when no algorithm was recognised", () => {
    setup({ algorithms: [] });
    expect(screen.getByText(/No named algorithm was recognised/)).toBeInTheDocument();
  });

  it("says so when complexity was not determined", () => {
    setup({ complexity: null });
    expect(screen.getByText("Complexity wasn't determined")).toBeInTheDocument();
  });

  it("shows a dash for cases that were not given", () => {
    const partial = {
      ...complexity!,
      functions: [{ ...complexity!.functions[0]!, bestCase: null, averageCase: undefined }],
    };
    setup({ complexity: partial });
    expect(screen.getByText("Best case").nextElementSibling).toHaveTextContent("—");
  });
});

describe("GrowthScale", () => {
  it("highlights the matching growth rate", () => {
    render(<GrowthScale value="O(n²)" />);
    const current = screen.getByRole("list").querySelector('[aria-current="true"]');
    expect(current).toHaveTextContent("O(n²)");
    expect(screen.getByText(/Quadratic growth slows down quickly/)).toBeInTheDocument();
  });

  it("recognises alternative spellings", () => {
    render(<GrowthScale value="O(n^2)" />);
    expect(screen.getByRole("list").querySelector('[aria-current="true"]')).toHaveTextContent(
      "O(n²)",
    );
  });

  it("is honest about shapes it does not cover", () => {
    render(<GrowthScale value="O(V + E)" />);
    expect(screen.getByRole("list").querySelector('[aria-current="true"]')).toBeNull();
    expect(screen.getByText(/not one of the common ones/)).toBeInTheDocument();
  });
});

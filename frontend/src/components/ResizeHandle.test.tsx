import { fireEvent, render, screen } from "@testing-library/react";
import { ResizeHandle } from "./ResizeHandle";

function setup(axis: "x" | "y" = "x") {
  const onChange = vi.fn();
  render(
    <ResizeHandle
      axis={axis}
      label="Resize chat"
      value={400}
      min={300}
      max={() => 500}
      onChange={onChange}
    />,
  );
  return { onChange, handle: screen.getByRole("separator", { name: "Resize chat" }) };
}

describe("ResizeHandle", () => {
  it("exposes its state to assistive tech", () => {
    const { handle } = setup();
    expect(handle).toHaveAttribute("aria-valuenow", "400");
    expect(handle).toHaveAttribute("aria-valuemin", "300");
    expect(handle).toHaveAttribute("aria-valuemax", "500");
    expect(handle).toHaveAttribute("aria-orientation", "vertical");
  });

  it("grows toward the start with ArrowLeft and shrinks with ArrowRight", () => {
    const { handle, onChange } = setup();
    fireEvent.keyDown(handle, { key: "ArrowLeft" });
    expect(onChange).toHaveBeenLastCalledWith(416);
    fireEvent.keyDown(handle, { key: "ArrowRight", shiftKey: true });
    expect(onChange).toHaveBeenLastCalledWith(336);
  });

  it("uses up/down arrows for the y axis", () => {
    const { handle, onChange } = setup("y");
    fireEvent.keyDown(handle, { key: "ArrowUp" });
    expect(onChange).toHaveBeenLastCalledWith(416);
  });

  it("clamps to min and max", () => {
    const { handle, onChange } = setup();
    fireEvent.keyDown(handle, { key: "Home" });
    expect(onChange).toHaveBeenLastCalledWith(300);
    fireEvent.keyDown(handle, { key: "ArrowLeft", shiftKey: true });
    fireEvent.keyDown(handle, { key: "End" });
    expect(onChange).toHaveBeenLastCalledWith(500);
  });

  it("ignores unrelated keys", () => {
    const { handle, onChange } = setup();
    fireEvent.keyDown(handle, { key: "a" });
    expect(onChange).not.toHaveBeenCalled();
  });
});

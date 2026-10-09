import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DEFAULT_SETTINGS } from "@/types/settings";
import { SettingsMenu } from "./SettingsMenu";

function setup() {
  const onChange = vi.fn();
  render(<SettingsMenu settings={DEFAULT_SETTINGS} onChange={onChange} />);
  return { onChange, trigger: screen.getByRole("button", { name: /settings/i }) };
}

async function open() {
  const ctx = setup();
  await userEvent.click(ctx.trigger);
  return ctx;
}

describe("SettingsMenu", () => {
  it("is closed until the trigger is clicked", async () => {
    const { trigger } = setup();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await userEvent.click(trigger);
    expect(screen.getByRole("dialog", { name: "Settings" })).toBeInTheDocument();
    expect(trigger).toHaveAttribute("aria-expanded", "true");
  });

  it("shows the current value of every setting", async () => {
    await open();
    expect(screen.getByRole("radio", { name: "System" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Medium" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Brief" })).toBeChecked();
  });

  it("offers Light, Dark and System themes", async () => {
    await open();
    const group = screen.getByRole("group", { name: "Theme" });
    expect(group.querySelectorAll("input")).toHaveLength(3);
    expect(screen.getByRole("radio", { name: "System" })).toBeInTheDocument();
  });

  it("reports each kind of change as a patch", async () => {
    const { onChange } = await open();
    await userEvent.click(screen.getByRole("radio", { name: "Dark" }));
    expect(onChange).toHaveBeenLastCalledWith({ theme: "dark" });
    await userEvent.click(screen.getByRole("radio", { name: "Large" }));
    expect(onChange).toHaveBeenLastCalledWith({ editorFontSize: "large" });
    await userEvent.click(screen.getByRole("radio", { name: "Detailed" }));
    expect(onChange).toHaveBeenLastCalledWith({ replyStyle: "detailed" });
  });

  it("closes on Escape and returns focus to the trigger", async () => {
    const { trigger } = await open();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("closes when clicking outside", async () => {
    await open();
    await userEvent.click(document.body);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

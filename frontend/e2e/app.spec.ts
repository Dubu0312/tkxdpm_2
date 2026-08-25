import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const API = "http://127.0.0.1:8917";

/** A wall-clock UTC value `minutes` from now, e.g. "2026-08-25T09:00:00". */
function at(minutes: number): string {
  return new Date(Date.now() + minutes * 60_000).toISOString().slice(0, 19);
}

async function clearSchedules(request: APIRequestContext): Promise<void> {
  const existing = await (await request.get(`${API}/api/schedules`)).json();
  for (const schedule of existing) {
    await request.delete(`${API}/api/schedules/${schedule.id}`);
  }
}

async function seed(
  request: APIRequestContext,
  title: string,
  startMinutes: number,
  endMinutes: number,
): Promise<void> {
  const response = await request.post(`${API}/api/schedules`, {
    data: {
      title,
      start_time: at(startMinutes),
      end_time: at(endMinutes),
      timezone: "UTC",
    },
  });
  expect(response.status(), await response.text()).toBe(201);
}

/** The cards listed under "Sắp tới", by title. */
function upcomingCards(page: Page) {
  return page.locator(".listsection .card__title");
}

test.beforeEach(async ({ request }) => {
  await clearSchedules(request);
});

test.describe("empty state", () => {
  test("invites the first schedule when there is nothing to show", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Chưa có lịch nào")).toBeVisible();
    // No section headings when there is nothing to divide.
    await expect(page.getByRole("heading", { name: "Sắp tới" })).toHaveCount(0);
    await expect(page.locator(".pastgroup")).toHaveCount(0);
    await expect(page.locator("#count")).toHaveText("0 lịch");
  });
});

test.describe("BUG-02 — upcoming and past are told apart", () => {
  test.beforeEach(async ({ request }) => {
    await seed(request, "Đã xong hôm qua", -24 * 60, -23 * 60);
    await seed(request, "Vừa kết thúc", -180, -120);
    await seed(request, "Đang họp", -30, 30);
    await seed(request, "Họp ngày kia", 2 * 24 * 60, 2 * 24 * 60 + 60);
  });

  test("only lists schedules that have not finished under “Sắp tới”", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Sắp tới" })).toBeVisible();

    await expect(upcomingCards(page)).toHaveText(["Đang họp", "Họp ngày kia"]);
    await expect(upcomingCards(page)).not.toContainText(["Đã xong hôm qua"]);
  });

  test("keeps finished schedules in a collapsed “Đã qua” group", async ({ page }) => {
    await page.goto("/");
    const summary = page.locator(".pastgroup__summary");
    await expect(summary).toHaveText("Đã qua (2)");

    // Collapsed: the finished cards are in the DOM but not shown.
    await expect(page.locator(".pastgroup .card__title").first()).toBeHidden();

    await summary.click();
    await expect(page.locator(".pastgroup .card__title")).toHaveText([
      "Vừa kết thúc",
      "Đã xong hôm qua", // most recent first
    ]);
  });

  test("marks a schedule that is happening right now", async ({ page }) => {
    await page.goto("/");
    const ongoing = page.locator(".card", { hasText: "Đang họp" });
    await expect(ongoing.getByText("Đang diễn ra")).toBeVisible();

    const later = page.locator(".card", { hasText: "Họp ngày kia" });
    await expect(later.getByText("Đang diễn ra")).toHaveCount(0);
  });

  test("says so plainly when everything is already over", async ({ page, request }) => {
    await clearSchedules(request);
    await seed(request, "Chỉ còn quá khứ", -300, -240);
    await page.goto("/");

    await expect(page.getByText("Không có lịch nào sắp tới.")).toBeVisible();
    await expect(page.locator(".pastgroup__summary")).toHaveText("Đã qua (1)");
  });

  test("a finished schedule can still be opened from the past group", async ({ page }) => {
    await page.goto("/");
    await page.locator(".pastgroup__summary").click();
    await page.locator(".pastgroup .card", { hasText: "Vừa kết thúc" }).click();
    await expect(page.locator("#panel").getByRole("heading", { name: "Vừa kết thúc" })).toBeVisible();
  });
});

test.describe("BUG-04 — validation speaks the app's language", () => {
  test("refuses an empty title in Vietnamese, in the app's own styling", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Tạo lịch" }).first().click();

    const title = page.getByLabel(/Tiêu đề/);
    await title.fill("");
    await page.getByRole("button", { name: "Tạo lịch", exact: true }).last().click();

    const error = page.locator(".field__error");
    await expect(error).toHaveText("Vui lòng nhập tiêu đề cho lịch.");
    await expect(page.getByText("Please fill out this field.")).toHaveCount(0);
  });

  test("keeps the browser's native bubble out of the way", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Tạo lịch" }).first().click();
    await expect(page.locator("form")).toHaveJSProperty("noValidate", true);
    // The constraint is still declared, so assistive technology still hears it.
    await expect(page.getByLabel(/Tiêu đề/)).toHaveAttribute("required", "");
  });

  test("marks the field invalid and puts the cursor in it", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Tạo lịch" }).first().click();
    const title = page.getByLabel(/Tiêu đề/);
    await title.fill("");
    await page.getByRole("button", { name: "Tạo lịch", exact: true }).last().click();

    await expect(title).toHaveAttribute("aria-invalid", "true");
    await expect(title).toBeFocused();
    const describedBy = await title.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();
    await expect(page.locator(`#${describedBy}`)).toHaveText("Vui lòng nhập tiêu đề cho lịch.");
  });

  test("scrolls the offending field clear of the sticky header", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Tạo lịch" }).first().click();
    const title = page.getByLabel(/Tiêu đề/);
    await title.fill("");
    // Click the submit button at the foot of a long form: the page is scrolled
    // away from the title, and focusing it has to bring it back into sight.
    await page.getByRole("button", { name: "Tạo lịch", exact: true }).last().click();

    const topbar = (await page.locator(".topbar").boundingBox())!;
    const field = (await title.boundingBox())!;
    expect(field.y).toBeGreaterThanOrEqual(topbar.y + topbar.height);
    await expect(page.locator(".field__error")).toBeInViewport();
  });

  test("catches a title of nothing but spaces, which the browser would allow", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Tạo lịch" }).first().click();
    await page.getByLabel(/Tiêu đề/).fill("   ");
    await page.getByRole("button", { name: "Tạo lịch", exact: true }).last().click();
    await expect(page.locator(".field__error")).toHaveText("Vui lòng nhập tiêu đề cho lịch.");
  });

  test("clears the message as soon as the field is filled in", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Tạo lịch" }).first().click();
    const title = page.getByLabel(/Tiêu đề/);
    await title.fill("");
    await page.getByRole("button", { name: "Tạo lịch", exact: true }).last().click();
    await expect(page.locator(".field__error")).toBeVisible();

    await title.fill("Họp nhóm");
    await expect(page.locator(".field__error")).toHaveCount(0);
    await expect(title).not.toHaveAttribute("aria-invalid", "true");
  });

  test("still creates the schedule once the form is valid", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Tạo lịch" }).first().click();
    await page.getByLabel(/Tiêu đề/).fill("Lịch hợp lệ");
    await page.getByRole("button", { name: "Tạo lịch", exact: true }).last().click();

    await expect(page.locator("#toast")).toContainText("Đã tạo lịch");
    await expect(page.locator("#panel").getByRole("heading", { name: "Lịch hợp lệ" })).toBeVisible();
  });
});

test.describe("no regressions in layout and accessibility", () => {
  test.beforeEach(async ({ request }) => {
    await seed(request, "Đã qua", -300, -240);
    await seed(request, "Sắp tới", 120, 180);
  });

  test("fits a phone screen without sideways scrolling", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    await expect(page.locator(".card").first()).toBeVisible();

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
  });

  test("fits a desktop screen without sideways scrolling", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/");
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
  });

  test("keeps one h1 and a heading order that does not skip a level", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);

    const levels = await page.evaluate(() =>
      [...document.querySelectorAll("h1,h2,h3,h4,h5,h6")].map((h) => Number(h.tagName[1])),
    );
    let previous = 0;
    for (const level of levels) {
      expect(level).toBeLessThanOrEqual(previous + 1);
      previous = level;
    }
  });

  test("opens the past group from the keyboard", async ({ page }) => {
    await page.goto("/");
    const summary = page.locator(".pastgroup__summary");
    await summary.focus();
    await expect(summary).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator(".pastgroup .card").first()).toBeVisible();
  });

  test("every form control has a name a screen reader can announce", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Tạo lịch" }).first().click();

    const unnamed = await page.evaluate(() => {
      const controls = [...document.querySelectorAll("form input, form select, form textarea")];
      return controls.filter((control) => {
        const label = control.closest("label")?.querySelector(".field__label")?.textContent ?? "";
        return label.trim() === "" && !control.getAttribute("aria-label");
      }).length;
    });
    expect(unnamed).toBe(0);
  });

  test("announces errors through a live region", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("#error")).toHaveAttribute("role", "alert");
    await expect(page.locator("#toast")).toHaveAttribute("aria-live", "polite");
  });
});

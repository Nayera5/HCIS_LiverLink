/** Apply job-title exclusions and capability checks while preserving each section's item order. */
export function filterNavigationSections(sections, can, jobTitle) {
  return sections.map((section) => ({
    ...section,
    items: section.items.filter((item) => !item.excludeJobTitles?.includes(jobTitle)
      && (!item.capability
        || (Array.isArray(item.capability) ? item.capability.some(can) : can(item.capability)))),
  })).filter((section) => section.items.length > 0)
}

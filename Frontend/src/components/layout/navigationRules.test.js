import assert from 'node:assert/strict'
import { test } from 'node:test'
import { filterNavigationSections } from './navigationRules.js'

const section = {
  label: 'Clinical',
  items: [
    { to: '/appointments', capability: 'appointments.view', excludeJobTitles: ['radiologist'] },
    { to: '/schedule', capability: 'schedules.manage_own' },
    { to: '/donor-applications', capability: 'donor_applications.view', excludeJobTitles: ['radiologist'] },
    { to: '/transplant', capability: 'transplant.view', excludeJobTitles: ['radiologist'] },
  ],
}

test('hides only the specified navigation items for Radiologists and preserves remaining order', () => {
  const sections = filterNavigationSections([section], () => true, 'radiologist')
  assert.deepEqual(sections.flatMap((item) => item.items.map((navItem) => navItem.to)), ['/schedule'])
})

test('keeps those items visible for other roles with the required capabilities', () => {
  for (const jobTitle of ['hepatologist', 'transplant_coordinator', 'transplant_surgeon', 'super_admin']) {
    const sections = filterNavigationSections([section], () => true, jobTitle)
    assert.deepEqual(
      sections.flatMap((item) => item.items.map((navItem) => navItem.to)),
      ['/appointments', '/schedule', '/donor-applications', '/transplant'],
      jobTitle,
    )
  }
})

test('continues to filter navigation by capability', () => {
  const sections = filterNavigationSections([section], (capability) => capability === 'appointments.view', 'radiologist')
  assert.deepEqual(sections.flatMap((item) => item.items.map((navItem) => navItem.to)), [])
})

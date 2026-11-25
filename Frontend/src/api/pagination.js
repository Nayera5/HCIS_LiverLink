const PAGE_SIZE = 100

export async function loadAllPages(fetchPage, params = {}) {
  const results = []
  let page = 1
  let response

  do {
    response = await fetchPage({ ...params, page, page_size: PAGE_SIZE })
    results.push(...response.results)
    page += 1
  } while (response.next)

  return results
}

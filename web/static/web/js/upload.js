// Wires every [data-upload] block: drag & drop or browse -> POST /api/files/ -> open the result.
import { api } from './api.js'
import { errorState } from './error-state.js'
import { h } from './dom.js'

function wire(root) {
  const drop = root.querySelector('[data-drop]'), input = root.querySelector('[data-input]')
  const card = root.querySelector('[data-card]'), errorBox = root.querySelector('[data-error]')

  const send = async (file) => {
    if (!file) return
    errorBox.replaceChildren()
    drop.hidden = true
    card.hidden = false
    card.querySelector('[data-card-name]').textContent = file.name
    card.querySelector('[data-card-meta]').textContent = `${(file.size / 1024).toFixed(1)} KB · uploading and processing…`
    try {
      const result = await api.upload(file)
      location.href = `/files/${result.id}/?replay=1`
    } catch (e) {
      card.hidden = true
      drop.hidden = false
      const again = h('button.btn', { type: 'button', text: 'Upload another file', onclick: () => { errorBox.replaceChildren(); input.click() } })
      errorBox.replaceChildren(errorState({ code: e.code, message: e.message, details: e.details, actions: [again] }))
      errorBox.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }

  root.querySelector('[data-browse]').addEventListener('click', () => input.click())
  input.addEventListener('change', () => { send(input.files[0]); input.value = '' })
  drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('is-over') })
  drop.addEventListener('dragleave', () => drop.classList.remove('is-over'))
  drop.addEventListener('drop', (e) => { e.preventDefault(); drop.classList.remove('is-over'); send(e.dataTransfer.files[0]) })
}

document.querySelectorAll('[data-upload]').forEach(wire)

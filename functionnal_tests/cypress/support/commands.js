import 'cypress-wait-until'

const userFixtures = {
  'administrators': 'defaultAdmin',
  'trusted-users': '',
  'users': 'baseUser'
}


let LOGIN_URL = '/api/v2/auth/login'

Cypress.Commands.add('loginAs', (role = 'administrators') => {
  if (getCookieValueFromEnv(role)) {
    cy.setSessionCookieFromEnv(role)
    return cy.getUserByRole(role)
  }
  cy.getUserByRole(role)
    .then(user => {
      return cy.request({
        method: 'POST',
        url: LOGIN_URL,
        body: {
          'email': user.email,
          'password': user.password
        }
      })
    })
    .then(response => {
      cy.waitUntil(() => cy.getCookie('session_key').then(cookie => {
        if (cookie && cookie.value) {
          return cy.saveCookieValue(role, cookie.value)
        }
        return false
      }))
      return cy.request({
        method: 'PUT',
        url: '/api/v2/users/' + response.body.user_id,
        body: {
          lang: 'en',
          public_name: response.body.public_name,
          timezone: 'Europe/Paris'
        }
      })
    })
    .then(response => response.body)
})

Cypress.Commands.add('logout', () => {
  cy.request('POST', 'api/v2/auth/logout')
  cy.cleanSessionCookies()
})

Cypress.Commands.add('typeInTinyMCE', (content) => {
  cy.window()
    .its('tinyMCE')
    .its('activeEditor')
    .then(activeEditor => {
      activeEditor.setContent(content)
      activeEditor.save()
    })
})

Cypress.Commands.add('assertTinyMCEContent', () => {
  cy.window({ timeout: 5000 })
    .its('tinyMCE')
    .its('activeEditor')
    .then(activeEditor => {
      activeEditor.getContent()
    })
})

Cypress.Commands.add('assertTinyMCEIsActive', (isActive = true) => {
  const message = (isActive ? 'tinyMCE is active' : 'tinyMCE is not active')
  cy.window().then(win => isActive
    ? assert.isNotNull(win.tinyMCE.activeEditor, message)
    : assert.isNull(win.tinyMCE.activeEditor, message)
  )
})

// INFO - CH - 2019-05-20 - see https://github.com/cypress-io/cypress/issues/170
Cypress.Commands.add('dropFixtureInDropZone', (fixturePath, fixtureMime, dropZoneSelector, fileTitle) => {
  const dropEvent = { dataTransfer: { files: [] } }
  cy.fixture(fixturePath, 'base64').then(fixture => {
    cy.window().then(window => {
      Cypress.Blob.base64StringToBlob(fixture, fixtureMime).then(blob => {
        const testFile = new window.File([blob], fileTitle)
        dropEvent.dataTransfer.files = [testFile]
      })
    })
  })

  // INFO - CH - 2019-06-12 - Adding a handler that bypass exception here because Cypress generates the following
  // "Uncaught Invariant Violation: Cannot call hover while not dragging."
  // Cypress then fail the test because it got an exception
  // Since the tests can continue even with this error, I bypass it, at least for now, because I can't find an
  // easy to fix it
  Cypress.on('uncaught:exception', (err, runnable) => false)
  cy.get(dropZoneSelector).trigger('drop', dropEvent)
  cy.removeAllListeners('uncaught:exception')
})

Cypress.Commands.add('waitForTinyMCELoaded', () => {
  cy.document().then($doc => {
    return new Cypress.Promise(resolve => { // Cypress will wait for this Promise to resolve
      const onTinyMceLoaded = () => {
        $doc.removeEventListener('tinymceLoaded', onTinyMceLoaded) // cleanup
        resolve() // resolve and allow Cypress to continue
      }
      $doc.addEventListener('tinymceLoaded', onTinyMceLoaded)
    })
  })
})

Cypress.Commands.add('form_request', (method, url, formData, done) => {
    const xhr = new XMLHttpRequest();
    xhr.open(method, url);
    xhr.send(formData);
})

Cypress.Commands.add('ignoreTinyMceError', () => {
  Cypress.on('uncaught:exception', (err, runnable) => {
      console.log('uncaught:exception')
      return false
    })
})

Cypress.Commands.add('saveCookieValue', (user, cookieValue) => {
  Cypress.env(`session_cookie_${user}`, cookieValue)
  return true
})

Cypress.Commands.add('setSessionCookieFromEnv', (user) => {
  cy.setCookie('session_key', getCookieValueFromEnv(user))
  cy.setCookie('lastConnection', '1')
  cy.setCookie('defaultLanguage', 'en')
})

const getCookieValueFromEnv = (user) => {
  return Cypress.env(`session_cookie_${user}`)
}

Cypress.Commands.add('cleanSessionCookies', () => {
  Cypress.env.reset()
})

Cypress.Commands.add('cancelXHR', () => {
  cy.visit('/api/v2/doc/')
})
